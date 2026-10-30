"""Numerically exercise the real GGML CPU mapped-weight loader on native Windows."""
import json
from pathlib import Path
import subprocess
import time
from build_openmoss_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return {**build_inputs(),**fingerprint('tools/test_openmoss_mapping.py')}


def run():
    before=inputs();binary,compilation=build()
    executable=binary.with_name('lma_openmoss_mapping_test.exe')
    folder=ROOT/'build/openmoss-mapping-tests'/('run-'+str(time.time_ns()))
    folder.mkdir(parents=True)
    result=subprocess.run([str(executable),str(folder)],capture_output=True,timeout=90)
    (folder/'stdout.txt').write_bytes(result.stdout);(folder/'stderr.txt').write_bytes(result.stderr)
    if result.returncode:raise RuntimeError('Inspect actual mapped-weight GGML contract: '+str(folder.relative_to(ROOT)))
    checks=json.loads(result.stdout)
    assert checks['passed']>=20 and all(checks[k] for k in ('mapped_cpu_graph_bitwise_equal','copy_on_write_preserves_file','sparse_offset_above_4gib','all_mappings_released'))
    current(before)
    value=dict(schema='lma.openmoss-mapping-contract/1',**checks,compilation=compilation,
        executable_sha256=sha(executable),capture_directory=folder.relative_to(ROOT).as_posix(),
        model_weights_used=False,physical_android=False,virtualization_used=False,input_fingerprint=before)
    # Sparse fixture is owned by this invocation; remove only that checked file
    # so source/evidence archives never include a multi-gigabyte sparse extent.
    sparse=(folder/'sparse.bin').resolve();sparse.relative_to((ROOT/'build/openmoss-mapping-tests').resolve());sparse.unlink()
    for p in (folder/'results.json',folder.parent/'results.json'):p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    return value


if __name__=='__main__':
    result=run();print(json.dumps({k:result[k] for k in ('passed','mapped_cpu_graph_bitwise_equal','sparse_offset_above_4gib','all_mappings_released')}))
