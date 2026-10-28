"""Fetch a pinned, source-only MOSS Delay fork; never fetch/convert model assets."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def validate_sources(lock):
    source = ROOT / 'build/native-src/moss-delay'
    if not source.exists():
        subprocess.run(['git', 'clone', '--filter=blob:none', '--no-checkout', lock['repository'], str(source)], check=True)
        subprocess.run(['git', '-C', str(source), 'sparse-checkout', 'set', '--cone', 'include', 'src', 'ggml', 'cmake', 'licenses', 'tools/tts'], check=True)
        subprocess.run(['git', '-C', str(source), 'checkout', '--detach', lock['revision']], check=True)
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip()
    if head != lock['revision'] or dirty:
        raise RuntimeError('Pinned MOSS source differs or has local files')
    for name, digest in lock['reviewed_files'].items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Reviewed MOSS source changed: ' + name)
    return source


def primitives(source, include_self_test=False):
    """Extract pinned native primitives only: no CLI, shell helper or Python/ONNX orchestration."""
    text = (source/'tools/tts/run-moss-tts-delay.cpp').read_text(encoding='utf-8')
    def section(start, end, last=False):
        a = text.rindex(start) if last else text.index(start)
        b = text.index(end, a+len(start)); return text[a:b]
    prefix = text[:text.index('static void print_usage(')]
    for name in ('arg.h', 'common.h', 'log.h'):
        prefix = prefix.replace('#include "'+name+'"\n', '')
    result = prefix + section('static bool parse_meta_i64(', 'static std::vector<llama_token> moss_encode_audio_llama(\n        const std::string & audio_encoder_model_path,\n        const std::string & wav_path,\n        int32_t n_gpu_layers,\n        uint32_t n_quantizers,\n        size_t * out_frames) {')
    result += section('static moss_prompt_input moss_build_prompt_input(', 'static int moss_run_audio_decoder_helper(', last=True)
    result += section('static moss_owned_batch moss_batch_from_packed_rows(', 'static void moss_generate_from_ref(')
    result += section('static std::vector<llama_token> moss_audio_history_slice(', 'static std::string moss_delay_config_to_string(')
    start = result.index('static void moss_write_codes_file(')
    result = result[:start] + result[result.index('static bool save_wav16(',start):]
    if include_self_test:
        a=text.rindex('static bool moss_delay_self_test(')
        result += text[a:text.index('\n} // namespace',a)]
    result += '\n} // namespace\n'
    if any(word in result for word in ('std::system(', 'int main(', 'common.h', 'arg.h', 'moss_run_audio_decoder_helper(')):
        raise RuntimeError('Native primitive extraction crossed an execution boundary')
    return result


if __name__ == '__main__':
    lock=json.loads((ROOT/'third_party/moss-delay-source-lock.json').read_text(encoding='utf-8'))
    print(validate_sources(lock))
