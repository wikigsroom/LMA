"""Reviewed instrumentation of build copies of two pinned native orchestrators."""
from pathlib import Path


def generated_sources(source: Path) -> dict[str, str]:
    result={}
    for rt in (False,True):
        name='moss_tts_rt.cpp' if rt else 'moss_tts_local.cpp'
        text=(source/'src'/name).read_text(encoding='utf-8')
        inserts=[
            ('    // 3. Embed prompt', '    lma_moss_rq::before_prefill('+('pr.S, int(pr.remaining_text.size())' if rt else 'S, 0')+', T_ref, opts.max_new_tokens);\n\n'),
            ('        ++n_steps;', '        lma_moss_rq::step(n_steps + 1, opts.max_new_tokens);\n'),
            ('    wav->clear();', '    lma_moss_rq::before_codec(T, '+('stop' if rt else 'stopped')+');\n'),
        ]
        for marker,addition in inserts:
            if text.count(marker)!=1:raise RuntimeError('Reviewed RQ seam changed: '+name+' '+marker)
            text=text.replace(marker,addition+marker,1)
        if rt:
            replacements={
                '    // 5. The time x depth generation loop.': '    auto stream = lma_moss_rq::run.audio ? codec_->stream_begin() : nullptr;\n    if (lma_moss_rq::run.audio && !stream) return false;\n    if (stream) wav->clear();\n\n    // 5. The time x depth generation loop.',
                '        if (stop) break;': '        if (stop) break;\n        if (stream) {\n            std::vector<float> chunk;\n            if (!codec_->stream_step(*stream, codes, &chunk) || chunk.size() != 1920) return false;\n            lma_moss_rq::run.audio(chunk, codec_->sample_rate());\n            wav->insert(wav->end(), chunk.begin(), chunk.end());\n        }',
                '    wav->clear();': '    if (stream) {\n        *sample_rate = codec_->sample_rate();\n        // A whole-clip RMS gain needs future samples. Incremental mode uses unity gain\n        // for BOTH the preview and final WAV; the nonstreaming path keeps upstream gain.\n        return true;\n    }\n    wav->clear();',
            }
            for marker,replacement in replacements.items():
                if text.count(marker)!=1:raise RuntimeError('Reviewed Realtime streaming seam changed: '+marker)
                text=text.replace(marker,replacement,1)
        result[name]='// Modified by LMA: bounded actual-prompt budgets, progress, and optional stateful Realtime audio.\n#include "policy.hpp"\n#include "audio_tokenizer.hpp"\n'+text
    header=(source/'include/moss_tts.h').read_text(encoding='utf-8')
    for marker,replacement in {
        'class AudioTokenizer;': 'struct NanoCodecStream;\nclass AudioTokenizer;',
        '    bool reconstruct(const std::vector<float>& wav, std::vector<float>* out);': '    bool reconstruct(const std::vector<float>& wav, std::vector<float>* out);\n    std::unique_ptr<NanoCodecStream> stream_begin();\n    bool stream_step(NanoCodecStream& state, const std::vector<int32_t>& codes, std::vector<float>* pcm);',
    }.items():
        if header.count(marker)!=1:raise RuntimeError('Reviewed codec declaration changed: '+marker)
        header=header.replace(marker,replacement,1)
    result['moss_tts.h']='// Modified by LMA: expose existing codec streaming methods; object layout unchanged.\n'+header
    return result
