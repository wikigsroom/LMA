"""Reviewed guards/loaders inserted into build copies; pristine pins stay clean."""
from pathlib import Path


def guarded_model(source: Path) -> str:
    text=(source/'src/model.cpp').read_text(encoding='utf-8')
    marker='// Phase 2: read the bytes from disk and upload to the already-bound backend.'
    allocation='''        self->m_aux->buffer = ggml_backend_alloc_ctx_tensors(self->m_aux->ctx, self->m_aux->backend);
        if (!self->m_aux->buffer) {
            throw std::runtime_error("Model::load: failed to allocate aux backend buffer ("
                                     + std::to_string(total_bytes / (1024 * 1024)) + " MiB)");
        }

        if (sc_spec.gctx) upload_tensor_data(sc_spec, *self->m_aux);
        upload_tensor_data(bb_spec, *self->m_aux);'''
    if text.count(marker)!=1 or text.count(allocation)!=1:
        raise RuntimeError('Pinned MOSS aux weight loader changed; review before building')
    adapter='''lma_openmoss::WeightSource mapped_source(const LoadSpec & spec, Model::Aux & aux) {
    lma_openmoss::WeightSource result{spec.path, {}};
    const uint64_t base = gguf_get_data_offset(spec.gctx);
    for (const auto & [name, alias] : spec.wanted) {
        const int64_t index = gguf_find_tensor(spec.gctx, name.c_str());
        if (index < 0) throw std::runtime_error("Missing mapped GGUF tensor: " + name);
        const uint64_t relative = gguf_get_tensor_offset(spec.gctx, index);
        if (relative > std::numeric_limits<uint64_t>::max() - base)
            throw std::runtime_error("Mapped GGUF tensor offset overflows");
        auto * tensor = alias == "_text_embed" ? aux.text_embed : aux.tensors.at(alias);
        result.tensors.push_back({tensor, base + relative});
    }
    return result;
}

'''
    mapped='''        if (ggml_backend_dev_type(ggml_backend_get_device(self->m_aux->backend)) == GGML_BACKEND_DEVICE_TYPE_CPU) {
            std::vector<lma_openmoss::WeightSource> sources;
            if (sc_spec.gctx) sources.push_back(mapped_source(sc_spec, *self->m_aux));
            sources.push_back(mapped_source(bb_spec, *self->m_aux));
            self->m_aux->buffer = lma_openmoss::map_cpu_weights(sources);
        } else {
'''+allocation+'''
        }'''
    return '// Modified by LMA: privately map CPU auxiliary GGUF weights without changing tensor bytes.\n#include "private_weights.hpp"\n'+text.replace(marker,adapter+marker).replace(allocation,mapped)


def guarded_pipeline(source: Path) -> str:
    text=(source/'src/pipeline.cpp').read_text(encoding='utf-8')
    assistant = '+ im_start + "assistant\\n" + build_assistant_prefix_block(tok, d, T_prefix);'
    if text.count(assistant) != 1: raise RuntimeError('Pinned assistant generation seam changed')
    # The official delay-family generation template ends after assistant\n.
    # Continuation and other architectures retain their own prefix handling.
    text = text.replace(assistant, '+ im_start + "assistant\\n" + '
        '((d.arch == Arch::TTSDelay && T_prefix == 0) ? std::string() : build_assistant_prefix_block(tok, d, T_prefix));')
    marker='    std::fprintf(stderr, "[generate] prompt_len = %d tokens\\n", prompt_len);'
    if text.count(marker)!=1:
        raise RuntimeError('Pinned MOSS generation seam changed; review before building')
    guard='    lma_openmoss::validate_generation_budget(prompt_len, req.max_new_tokens, int(llama_n_ctx(model.backbone_ctx())));\n'
    ambient='    s += "- Ambient Sound:\\nNone\\n";'
    if text.count(ambient)!=1:raise RuntimeError('Pinned ambient-conditioning seam changed')
    text=text.replace(ambient,'    s += "- Ambient Sound:\\n" + lma_openmoss::generation_budget.ambient_sound + "\\n";')
    sampled='        last_step = decoder->step(text_logits, hidden_vec, req.sampling);'
    decode='            result.waveform = codec_decode(model, codes.data(), nvq_out, t_audio);'
    if text.count(sampled)!=1 or text.count(decode)!=1:
        raise RuntimeError('Pinned actual sampling/codec seam changed; review before building')
    text=text.replace(sampled,sampled+'\n        lma_openmoss::generation_step(step + 1, req.max_new_tokens, last_step.stop);')
    text=text.replace(decode,'            lma_openmoss::generation_decoding();\n'+decode)
    return '// Modified by LMA: official delay assistant prefix, budgets, ambient conditioning and actual generation progress.\n#include "generation_guard.hpp"\n'+text.replace(marker,guard+marker)


def prompt_primitives(source: Path) -> str:
    """Actual pinned formatting functions, using the real public request types."""
    text=guarded_pipeline(source)
    defaults=text[text.index('std::string default_or_none('):text.index('// Convert a token id')]
    body=text[text.index('std::string build_user_inst('):text.index('// Build the full assistant-prompt string:')]
    if any(x in defaults+body for x in ('llama_', 'ggml_', 'Model &', 'Tokenizer &')):
        raise RuntimeError('Prompt primitive extraction crossed a graph boundary')
    return '#include "openmoss/pipeline.h"\nnamespace openmoss {\n'+defaults+body+'\n}\n'


def guarded_delay(source: Path) -> str:
    """Align real delayed-state updates/extraction with the pinned processor."""
    text = (source / 'src/delay.cpp').read_text(encoding='utf-8')
    update = '    } else if (m_delayed_length >= 0) {\n        m_delayed_length++;'
    boundary = '    if (start < 0) return {};'
    threshold = '    if (T <= int64_t(m_dims.n_vq)) return {};'
    length = '    const int64_t T_audio = T - int64_t(m_dims.n_vq);'
    for seam in [update, boundary, threshold, length]:
        if text.count(seam) != 1: raise RuntimeError('Pinned MOSS delay seam changed; review before building')
    begin = text.index('    // delayed_length convention here differs')
    end = text.index('    if (m_delayed_length < 0 && next_text', begin)
    text = text[:begin] + ('    // Official generation starts the flush at zero and increments it in\n'
        '    // that same step. Extraction removes n_vq - 1 trailing delay rows.\n') + text[end:]
    text = text.replace(update, '    }\n    if (m_delayed_length >= 0) {\n        m_delayed_length++;')
    text = text.replace(boundary, boundary + '\n'
        '    // User reference slots are never generated assistant output.\n'
        '    if (start < int64_t(m_history.size()) &&\n'
        '        m_history[size_t(start)].front() == m_dims.audio_user_slot_token_id) return {};')
    text = text.replace(threshold, '    if (T < int64_t(m_dims.n_vq)) return {};')
    text = text.replace(length, '    const int64_t T_audio = T - int64_t(m_dims.n_vq) + 1;')
    return '// Modified by LMA: match official flush timing/frame extraction; exclude user reference output.\n' + text


def guarded_codec(source: Path) -> str:
    """Release only completed CPU encoder scratch, after output codes are copied."""
    text = (source / 'src/codec.cpp').read_text(encoding='utf-8')
    seam = ('    ggml_free(gctx);\n    return out;\n}\n\n'
        '// ───────────────────────────────────────────────────────────────────────────\n'
        '// Model ctor/dtor + CodecGraphs accessor.')
    if text.count(seam) != 1: raise RuntimeError('Pinned MOSS encoder lifetime seam changed; review before building')
    replacement = seam.replace('    return out;',
        '    lma_openmoss::release_encoder_scratch(m_galloc, aux->backend);\n    return out;')
    return ('// Modified by LMA: release completed CPU reference encoder scratch before generation.\n'
        '#include "codec_memory.hpp"\n' + text.replace(seam, replacement))
