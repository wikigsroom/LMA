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
    return '// Modified by LMA: enforce budgets, bind ambient conditioning, report actual sampled steps and termination.\n#include "generation_guard.hpp"\n'+text.replace(marker,guard+marker)


def prompt_primitives(source: Path) -> str:
    """Actual pinned formatting functions, using the real public request types."""
    text=guarded_pipeline(source)
    defaults=text[text.index('std::string default_or_none('):text.index('// Convert a token id')]
    body=text[text.index('std::string build_user_inst('):text.index('// Build the full assistant-prompt string:')]
    if any(x in defaults+body for x in ('llama_', 'ggml_', 'Model &', 'Tokenizer &')):
        raise RuntimeError('Prompt primitive extraction crossed a graph boundary')
    return '#include "openmoss/pipeline.h"\nnamespace openmoss {\n'+defaults+body+'\n}\n'
