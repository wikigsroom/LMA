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
        result[name]='// Modified by LMA: strict actual-prompt budgets and bounded progress/timing events.\n#include "policy.hpp"\n'+text
    return result
