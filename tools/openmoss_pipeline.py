"""One reviewed context guard inserted into a build copy; pristine pin stays clean."""
from pathlib import Path


def guarded_pipeline(source: Path) -> str:
    text=(source/'src/pipeline.cpp').read_text(encoding='utf-8')
    marker='    std::fprintf(stderr, "[generate] prompt_len = %d tokens\\n", prompt_len);'
    if text.count(marker)!=1:
        raise RuntimeError('Pinned MOSS generation seam changed; review before building')
    guard='    lma_openmoss::validate_generation_budget(prompt_len, req.max_new_tokens, int(llama_n_ctx(model.backbone_ctx())));\n'
    ambient='    s += "- Ambient Sound:\\nNone\\n";'
    if text.count(ambient)!=1:raise RuntimeError('Pinned ambient-conditioning seam changed')
    text=text.replace(ambient,'    s += "- Ambient Sound:\\n" + lma_openmoss::generation_budget.ambient_sound + "\\n";')
    return '// Modified by LMA: enforce prefill budgets and bind explicit ambient conditioning for old SoundEffect.\n#include "generation_guard.hpp"\n'+text.replace(marker,guard+marker)


def prompt_primitives(source: Path) -> str:
    """Actual pinned formatting functions, using the real public request types."""
    text=guarded_pipeline(source)
    defaults=text[text.index('std::string default_or_none('):text.index('// Convert a token id')]
    body=text[text.index('std::string build_user_inst('):text.index('// Build the full assistant-prompt string:')]
    if any(x in defaults+body for x in ('llama_', 'ggml_', 'Model &', 'Tokenizer &')):
        raise RuntimeError('Prompt primitive extraction crossed a graph boundary')
    return '#include "openmoss/pipeline.h"\nnamespace openmoss {\n'+defaults+body+'\n}\n'
