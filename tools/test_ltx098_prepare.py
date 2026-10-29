"""Exercise native local conversion, rollback and trained byte parity; no inference."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import threading
import time
import numpy as np
from evidence import fingerprint, current
from build_ltx098_prepare import inputs as build_inputs
from ltx098_assets import Checkpoint, validate_transformer, gguf_header, sha, PREFIX
from export_ltx098 import convert
from test_ltx098_text import execute

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'build/ltx098-prepare-host/bin/lma_ltx098_prepare.exe'
OUT = ROOT / 'build/ltx098-prepare-tests'
SOURCE = ROOT / 'build/ltx098-trained/originals/ltxv-2b-0.9.8-distilled.safetensors'
PYTHON_GGUF = ROOT / 'build/ltx098-trained/converted/ltx098-dit.gguf'
SOURCE_SHA = '76aa8c4786af752fa6f951947129d5290c3c6c0b2fadcadea6b5e114ae2cad8f'
OUTPUT_SHA = 'ef29c886b36f8a1dbc6693002256049407e512da7a61bf2cc750f1d4d2277ebf'


def inputs():
    return fingerprint('research/ltx098_prepare', 'research/local_prepare', 'tools/build_ltx098_prepare.py', 'tools/test_ltx098_prepare.py',
                       'tools/test_ltx098_text.py', 'tools/ltx098_assets.py', 'tools/export_ltx098.py',
                       'third_party/ltx098-source-lock.json', 'third_party/ltx098-text-source-lock.json')


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False) + '\n', encoding='utf-8')


def fixture(path):
    """Conversion-only fixture: no neural inference or trained/phone claim."""
    base = json.loads((ROOT / 'third_party/ltx098-source-lock.json').read_text(encoding='utf-8'))['checkpoint_transformer_config']
    config = dict(base, num_attention_heads=2, attention_head_dim=12, cross_attention_dim=24,
                  caption_channels=32, in_channels=8, out_channels=8, num_layers=2)
    half_bits = np.arange(65536, dtype='<u2')
    half_bits = half_bits[(half_bits & 0x7c00) != 0x7c00]
    bf16_bits = np.arange(65536, dtype='<u2')
    bf16_bits = bf16_bits[(bf16_bits & 0x7f80) != 0x7f80]
    bf16_float = (bf16_bits.astype('<u4') << 16).view('<f4')
    half_positive = np.arange(0x7bff, dtype='<u2').view('<f2').astype('<f4')
    half_next = np.arange(1, 0x7c00, dtype='<u2').view('<f2').astype('<f4')
    midpoint = (half_positive + half_next) * np.float32(.5)
    ties = np.concatenate([np.nextafter(midpoint, np.float32(-np.inf)), midpoint,
                           np.nextafter(midpoint, np.float32(np.inf))])
    ties = np.concatenate([ties, -ties, np.array([65504., -65504., 0., -0.], dtype='<f4')]).astype('<f4')
    specs = [
        ('half.weight', 'F16', [2, len(half_bits)//2], half_bits.tobytes()),
        ('half.bias', 'F16', [len(half_bits)], half_bits.tobytes()),
        ('bf16.bias', 'BF16', [len(bf16_bits)], bf16_bits.tobytes()),
        ('bf16.weight', 'BF16', [1, int(np.sum(np.abs(bf16_float) <= 65504))], bf16_bits[np.abs(bf16_float) <= 65504].tobytes()),
        ('round.weight', 'F32', [1, len(ties)], ties.tobytes()),
    ]
    for i in range(60):
        shape = [] if i % 3 == 0 else [1, 2, 3] if i % 3 == 1 else [1, 1, 2, 1, 3]
        data = (np.arange(int(np.prod(shape)), dtype='<f4') * np.float32(.125)).tobytes()
        specs.append((f'scalar-{i}.bias', 'F32', shape, data))
    header = {}; payload = bytearray()
    for name, dtype, shape, data in specs:
        first = len(payload); payload.extend(data)
        header[PREFIX + name] = dict(dtype=dtype, shape=shape, data_offsets=[first, len(payload)])
    # These unused component bytes still belong to the verified source identity.
    header['vae.unused'] = dict(dtype='F16', shape=[3], data_offsets=[len(payload), len(payload)+6])
    payload.extend(b'\x00\x00\x00\x80\x00\x3c')
    header = dict(reversed(list(header.items())))
    header['__metadata__'] = dict(config=json.dumps(dict(transformer=config), separators=(',', ':')))
    save_checkpoint(path, header, payload)
    return header, payload, dict(finite_half_patterns=len(half_bits), finite_bf16_patterns=len(bf16_bits),
                                 float32_rounding_values=len(ties), tensor_header_order_differs_from_payload=True)


def save_checkpoint(path, header, payload, raw_header=None):
    raw = raw_header if raw_header is not None else json.dumps(header, separators=(',', ':')).encode()
    path.write_bytes(struct.pack('<Q', len(raw)) + raw + payload)


def run(trained=False):
    before = inputs()
    receipts = {}
    for name in ['host', 'arm64']:
        receipt = json.loads((ROOT / f'build/ltx098-prepare-{name}/receipt.json').read_text(encoding='utf-8'))
        current(receipt['input_fingerprint'])
        if receipt['input_fingerprint'] != build_inputs(): raise RuntimeError('Wrong preparation build inputs')
        binary = EXE if name == 'host' else ROOT / 'build/ltx098-prepare-arm64/bin/liblma-ltx098-prepare.so'
        if sha(binary) != receipt['executable_sha256']: raise RuntimeError('Changed preparation binary')
        receipts[name] = receipt
    OUT.mkdir(exist_ok=True)
    (OUT / 'results.json').unlink(missing_ok=True)
    directory = OUT / ('run-' + str(time.time_ns())); directory.mkdir()
    checks = []; jobs = []; children = 0; guards = 0

    def check(condition, name):
        checks.append(dict(name=name, passed=bool(condition)))
        if not condition: raise RuntimeError('Failed: ' + name)

    def invoke(name, request, success=True, fixture_mode=True, raw_request=None, observe=False):
        nonlocal children, guards
        if not success and request.get('output_name') == 'fixture-output':
            request = dict(request, output_name='guard-' + name)
        path = directory / (name + '.request.json')
        if raw_request is None: write(path, request)
        else: path.write_text(raw_request, encoding='utf-8')
        command = [str(EXE)] + (['--fixture'] if fixture_mode else []) + [str(path)]
        result, seconds, resources = execute(command, timeout=900, observe=observe); children += 1
        (directory / (name + '.stdout.json')).write_bytes(result.stdout)
        (directory / (name + '.progress.jsonl')).write_bytes(result.stderr)
        response = json.loads(result.stdout.decode('utf-8'))
        check((result.returncode == 0) == success and response['ok'] is success, name + ': exit and result')
        if not success:
            guards += 1
            check(not any(p.name.startswith('.ltx098-prepare-') for p in directory.iterdir()), name + ': no abandoned stage')
            target = request.get('output_name')
            if target and target not in ('existing-file', 'existing-directory', 'raced-directory'):
                # Invalid names must not be resolved for any mutation.
                if target.replace('-', '').replace('_', '').isalnum(): check(not (directory / target).exists(), name + ': no partial output')
        jobs.append(dict(name=name, seconds=seconds, success=success, native=response, resources=resources))
        return response

    tiny = directory / 'untrained-conversion.safetensors'; header, payload, coverage = fixture(tiny)
    tiny_hash = sha(tiny)
    base = dict(operation='convert_dit', checkpoint=str(tiny), expected_source_bytes=tiny.stat().st_size,
                expected_source_sha256=tiny_hash, storage_root=str(directory), output_name='fixture-output')
    # NumPy/Python implementation is independent of the portable writer and hash/half routines.
    reference = directory / 'python-reference'; python_result = convert(tiny, reference, fixture=True)
    response = invoke('fixture-convert', base)
    native = directory / 'fixture-output/ltx098-dit.gguf'
    check(native.read_bytes() == (reference / 'ltx098-dit.gguf').read_bytes(), 'all fixture tensors/header/padding byte parity')
    check(response['output_sha256'] == sha(native) == python_result['sha256'], 'fixture SHA matches hashlib')
    check(response['source_sha256'] == tiny_hash and response['source_sha256_verified'], 'fixture complete source hash')
    check(response['source_streamed_bytes'] == tiny.stat().st_size, 'all unused component bytes streamed')
    check(response['output_written_bytes'] == native.stat().st_size == response['output_bytes'], 'fixture output accounting')
    check(json.loads((native.parent / 'conversion.json').read_text(encoding='utf-8')) == response, 'transaction receipt is exact response')
    again = invoke('fixture-repeat', dict(base, output_name='fixture-repeat'))
    check(again['output_sha256'] == response['output_sha256'], 'separate conversion deterministic')
    inspection = dict(base, operation='inspect_dit'); inspection.pop('storage_root'); inspection.pop('output_name')
    inspected = invoke('inspect-only', inspection)
    check(not inspected['source_sha256_verified'] and 'output_sha256' not in inspected, 'metadata inspection never claims payload verification')
    invoke('fixture-not-production', inspection, success=False, fixture_mode=False)
    invoke('unknown-operation', dict(base, operation='download'), success=False)
    invoke('unknown-request-field', dict(base, fixture=True), success=False)
    raw = json.dumps(base)
    invoke('duplicate-request', base, success=False, raw_request=raw[:-1]+',"operation":"convert_dit"}')
    invoke('nested-request', base, success=False, raw_request='['*34+'0'+']'*34)
    invoke('oversized-request', base, success=False, raw_request=' '*32769)
    invoke('inspect-output', dict(base, operation='inspect_dit'), success=False)
    invoke('wrong-source-bytes', dict(base, expected_source_bytes=tiny.stat().st_size+1), success=False)
    invoke('negative-source-bytes', dict(base, expected_source_bytes=-1), success=False)
    invoke('boolean-source-bytes', dict(base, expected_source_bytes=True), success=False)
    invoke('bad-sha-format', dict(base, expected_source_sha256='G'*64), success=False)
    invoke('wrong-source-sha', dict(base, expected_source_sha256='0'*64, output_name='wrong-sha'), success=False)
    invoke('disk-budget', dict(base, max_output_bytes=1), success=False)
    invoke('missing-source', dict(base, checkpoint=str(directory/'absent')), success=False)
    invoke('remote-source', dict(base, checkpoint='https://example.invalid/model'), success=False)
    invoke('relative-source', dict(base, checkpoint='untrained-conversion.safetensors'), success=False)
    invoke('missing-storage', dict(base, storage_root=str(directory/'absent')), success=False)
    for i, name in enumerate(['..', '../escape', 'CON', 'NUL.txt', 'LPT1', 'trailing.', '.hidden', 'space name', 'x'*97]):
        invoke(f'basename-{i}', dict(base, output_name=name), success=False)
    existing_file = directory/'existing-file'; existing_file.write_bytes(b'keep-user-file')
    existing_dir = directory/'existing-directory'; existing_dir.mkdir(); (existing_dir/'user').write_bytes(b'keep-user-directory')
    for name in ['existing-file','existing-directory']:
        invoke(name, dict(base, output_name=name), success=False)
    check(existing_file.read_bytes() == b'keep-user-file' and (existing_dir/'user').read_bytes() == b'keep-user-directory', 'existing user assets preserved')
    cancelled = directory/'cancel'; cancelled.touch()
    invoke('pre-cancel', dict(base, cancel_file=str(cancelled)), success=False)

    def malformed(name, change=None, blob=None, raw=None):
        altered = copy.deepcopy(header)
        if change: change(altered)
        path = directory/(name+'.safetensors'); save_checkpoint(path, altered, payload if blob is None else blob, raw_header=raw)
        request = dict(base, checkpoint=str(path), expected_source_bytes=path.stat().st_size, expected_source_sha256=sha(path), output_name=name)
        invoke(name, request, success=False)

    first = PREFIX+'half.weight'
    malformed('duplicate-header', raw=b'{"a":1,"a":2}')
    malformed('duplicate-config', lambda h:h['__metadata__'].update(config='{"transformer":{},"transformer":{}}'))
    malformed('missing-metadata', lambda h:h.pop('__metadata__'))
    malformed('unsupported-dtype', lambda h:h[first].update(dtype='I32'))
    malformed('overlap', lambda h:h[first].update(data_offsets=[1,h[first]['data_offsets'][1]+1]))
    malformed('shape-overflow', lambda h:h[first].update(shape=[1000000]*5))
    malformed('boolean-shape', lambda h:h[first].update(shape=[True]))
    malformed('unknown-tensor-field', lambda h:h[first].update(url='https://example.invalid'))
    malformed('trailing-source', blob=payload+b'X')
    malformed('incomplete-transformer', lambda h:h.pop(PREFIX+'scalar-0.bias'))
    for name, change in [('wrong-config',dict(norm_eps=.1)),('wrong-config-type',dict(attention_bias=1)),('fixture-dimensions',dict(num_attention_heads=3))]:
        def edit(h, update=change):
            config=json.loads(h['__metadata__']['config']);config['transformer'].update(update);h['__metadata__']['config']=json.dumps(config)
        malformed(name, edit)
    altered = bytearray(payload); altered[:2] = b'\x00\x7c'
    malformed('nonfinite-parameter', blob=altered)
    f32_name = PREFIX+'round.weight'; position=header[f32_name]['data_offsets'][0]
    altered = bytearray(payload); altered[position:position+4] = struct.pack('<f',65520.)
    malformed('f16-overflow', blob=altered)
    check(sha(tiny) == tiny_hash, 'source retained byte identical after all guards')

    # Exercise conversion-time cancellation and competing commit after output creation.
    # A source with a bounded fixture architecture and a 64-MiB unused component
    # makes cancellation deterministic without any model execution.
    large_header = copy.deepcopy(header); large_payload = bytearray(payload); end=len(large_payload)
    large_header['unused.large'] = dict(dtype='F16', shape=[1024,32768], data_offsets=[end,end+64*1024*1024])
    large_payload.extend(b'\0'*(64*1024*1024)); large = directory/'cancel-source.safetensors'
    save_checkpoint(large,large_header,large_payload); del large_payload
    large_sha = sha(large)
    for name in ['mid-cancel', 'commit-race']:
        flag=directory/(name+'.cancel'); target=directory/('raced-directory' if name=='commit-race' else name)
        request=dict(base,checkpoint=str(large),expected_source_bytes=large.stat().st_size,expected_source_sha256=large_sha,
                     output_name=target.name,cancel_file=str(flag))
        request_path=directory/(name+'.request.json');write(request_path,request)
        child=subprocess.Popen([str(EXE),'--fixture',str(request_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT)
        children+=1; start=time.monotonic(); progress_lines=[]
        try:
            first_line=child.stderr.readline(); progress_lines.append(first_line)
            check(json.loads(first_line)['phase']=='convert',name+': actual streaming began')
            if name=='mid-cancel': flag.touch()
            else: target.mkdir();(target/'user').write_bytes(b'competing-user-asset')
            stdout,stderr=child.communicate(timeout=60);progress_lines.append(stderr)
            (directory/(name+'.progress.jsonl')).write_bytes(b''.join(progress_lines));(directory/(name+'.stdout.json')).write_bytes(stdout)
            result=json.loads(stdout)
            check(child.returncode==1 and not result['ok'],name+': failed locally');guards+=1
            if name=='mid-cancel':check(result['error']=='Cancelled' and not target.exists(),name+': cancellation rollback')
            else:check((target/'user').read_bytes()==b'competing-user-asset',name+': exclusive commit preserves competitor')
            check(not any(p.name.startswith('.ltx098-prepare-') for p in directory.iterdir()),name+': owned staging cleaned')
            jobs.append(dict(name=name,success=False,native=result,seconds=time.monotonic()-start,resources=dict(observed=False)))
        finally:
            if child.poll() is None:child.kill();child.communicate(timeout=10)
    check(sha(large)==large_sha,'cancel/race source preserved')
    trained_result = None
    if trained:
        check(SOURCE.stat().st_size==6340744492,'reviewed trained source bytes')
        checkpoint=Checkpoint(SOURCE);config,items=validate_transformer(checkpoint)
        python_header,_,payload_bytes=gguf_header(config,items,SOURCE_SHA)
        request=dict(operation='inspect_dit',checkpoint=str(SOURCE),expected_source_bytes=6340744492,expected_source_sha256=SOURCE_SHA)
        inspected=invoke('trained-inspect',request,fixture_mode=False)
        check(inspected['gguf_header_sha256']==hashlib.sha256(python_header).hexdigest(),'trained header matches independent Python before conversion')
        check(inspected['output_bytes']==len(python_header)+payload_bytes==3849516416,'trained output size planned')
        converted=invoke('trained-convert',dict(request,operation='convert_dit',storage_root=str(directory),output_name='trained-output'),fixture_mode=False,observe=True)
        output=directory/'trained-output/ltx098-dit.gguf'
        check(converted['source_sha256_verified'] and converted['source_sha256']==SOURCE_SHA,'all 6.34-GB trained source SHA verified in stream')
        check(converted['output_sha256']==sha(output)==sha(PYTHON_GGUF)==OUTPUT_SHA,'all 3.85-GB trained output byte identity with Python baseline')
        check(converted['tensors']==715 and converted['source_tensor_count']==944 and converted['parameters']==1923385472,'all trained DiT parameters converted')
        check(converted['output_written_bytes']==output.stat().st_size==3849516416,'trained exact byte accounting')
        job=jobs[-1]
        check(job['resources']['observed'] and job['resources']['samples']>0,'actual trained child memory measured')
        check(job['resources']['observed_peak_working_set_bytes']<128*1024*1024,'trained conversion stays under 128-MiB observed host working set')
        trained_result=dict(native=converted,seconds=job['seconds'],resources=job['resources'],
                            python_output_sha256=OUTPUT_SHA,whole_output_sha256_independently_recomputed=True)
    current(before)
    record=dict(schema='lma.ltx098-native-prepare-tests/1',passed=True,checks=len(checks),guards=guards,native_children=children,
                actual_trained_conversions=1 if trained else 0,trained=trained_result,fixture_coverage=coverage,jobs=jobs,
                builds=receipts,source_inference=False,model_data_embedded=False,engine_registered=False,packaged_in_apk=False,
                physical_android=False,complete_video_pipeline=False,release_ready=False,virtualization_used=False,
                artifacts_directory=str(directory.relative_to(ROOT)).replace('\\','/'),input_fingerprint=before)
    write(directory/'checks.json',checks);write(directory/'results.json',record);write(OUT/'results.json',record)
    print(json.dumps({k:record[k] for k in ['passed','checks','guards','native_children','actual_trained_conversions','artifacts_directory']}),flush=True)
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--trained',action='store_true');run(parser.parse_args().trained)
