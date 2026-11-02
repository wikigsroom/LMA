"""Export/check supplementary direct-LAN evidence without changing released assets."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import shutil
import subprocess

from evidence import ROOT, current, fingerprint, version


PUBLIC = ROOT/'verification/supplemental'/('v'+version())/'lan-http.json'
MEDIA = ROOT/'docs/media/tests'/('lan-http-v'+version().replace('.',''))


def read(path):
    return Path(path).read_text(encoding='utf8')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check():
    data=json.loads(read(PUBLIC))
    assert data['schema']=='lma.physical-lan-http/1' and data['status']=='passed'
    assert data['version']==version() and data['passed']==len(data['checks'])>=50
    assert all(c['passed'] for c in data['checks']) and data['http_requests']>100
    current(data['input_fingerprint']);current(data['exporter_input_fingerprint'])
    assert data['apk_sha256']==json.loads(read(ROOT/'dist/build-info.json'))['sha256']
    for flag in ('tcp_endpoints_verified','physical_pc_adapter_verified','lan_left_enabled',
                 'user_history_preserved','model_settings_preserved'):
        assert data[flag]
    for flag in ('proxy_used','adb_port_forward_used','virtualization_used','model_downloads',
                 'remote_inference','new_video_generated','quality_accepted','background_endurance_tested'):
        assert not data[flag]
    if version()=='0.3.13':
        assert data['api_port']==52187 and data['previous_default_port']==8080 and data['upgrade_verified']
    else:
        assert 1024<=data['api_port']<=65535
    assert data['generation_deadline_seconds'] is None and len(data['outputs'])==3
    assert sum(o['operation']=='speech.synthesize' for o in data['outputs'])==2
    assert sum(o['operation']=='image.generate' for o in data['outputs'])==1
    assert data['existing_video']['duration_seconds']>5 and not data['existing_video']['newly_generated']
    manifest=json.loads(read(MEDIA/'manifest.json'))
    assert manifest['apk_sha256']==data['apk_sha256'] and manifest['privacy_reviewed']
    assert manifest['media_kind']=='Physical screenshot and new phone-generated PNG/WAV; existing video is linked, not regenerated'
    assert len(manifest['files'])==4
    for item in manifest['files']:
        path=MEDIA/item['file']
        assert path.parent==MEDIA and path.stat().st_size==item['bytes'] and digest(path)==item['sha256']
    return dict(passed=data['passed'],http_requests=data['http_requests'],
                physical_direct_lan_tested=True,phone_generated_outputs=len(data['outputs']),
                existing_video_seconds=data['existing_video']['duration_seconds'],
                published_release_assets_changed=False)


def export(path):
    path=Path(path).resolve();raw=json.loads(read(path));current(raw['input_fingerprint'])
    assert raw['status']=='passed' and raw['passed']==len(raw['checks'])
    proof=path.parent/'connection-proof-private.json';connections=json.loads(read(proof))
    assert len(connections)==raw['http_requests']
    sources={c['local'][0] for c in connections};targets={tuple(c['peer']) for c in connections}
    assert len(sources)==len(targets)==1
    source=ipaddress.IPv4Address(next(iter(sources)));target,port=next(iter(targets))
    assert source.is_private and not source.is_loopback and target!=str(source)
    assert ipaddress.IPv4Address(target).is_private and not ipaddress.IPv4Address(target).is_loopback
    assert 1<=port<=65535
    # Validate the selected Windows interface rather than assuming every private
    # address belongs to a physical adapter. No virtual runtime is invoked.
    script=("$entry=Get-NetIPAddress -AddressFamily IPv4 -IPAddress '"+str(source)+"'; "
            'Get-NetAdapter -InterfaceIndex $entry.InterfaceIndex | '
            'Select-Object HardwareInterface,Status | ConvertTo-Json -Compress')
    adapter=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive',
        '-Command',script],text=True,encoding='utf8'))
    assert adapter['HardwareInterface'] and adapter['Status']=='Up'
    # Explicit allowlist: no address, serial, key, private state, request body,
    # personal history or raw TCP connection log can enter the public record.
    keys=('schema','status','started_at','finished_at','version','apk_sha256','device',
          'input_fingerprint','checks','passed','outputs','published_models','published_operation_counts',
          'catalogue_latency_ms','screen_off','http_requests','tcp_endpoints_verified',
          'transport','generation_deadline_seconds','proxy_used','adb_port_forward_used',
          'virtualization_used','model_downloads','remote_inference','new_video_generated',
          'existing_video','quality_accepted','background_endurance_tested','lan_left_enabled',
          'user_history_preserved','model_settings_preserved','lan_enabled_by_test','api_port','upgrade_verified','previous_default_port')
    data={k:raw[k] for k in keys if k in raw}
    data['physical_pc_adapter_verified']=True
    data['exporter_input_fingerprint']=fingerprint('tools/export_lan_http_evidence.py')
    data['private_tcp_proof_sha256']=digest(proof)
    data['app_release_tag']='v'+version()
    data['scope']='Supplementary direct LAN HTTP; three new phone-local PNG/WAV outputs; existing video transfer only. No production gateway, all-model quality or endurance acceptance.'
    MEDIA.mkdir(parents=True,exist_ok=True);files=[]
    for item in [*raw['outputs'],raw['media']]:
        source=path.parent/item['file']
        assert source.parent==path.parent and source.stat().st_size==item['bytes']
        assert digest(source)==item['sha256']
        shutil.copy2(source,MEDIA/item['file'])
        files.append({k:item[k] for k in ('file','bytes','sha256')})
    media=dict(schema='lma.physical-lan-http-media/1',version=data['version'],apk_sha256=data['apk_sha256'],
        media_kind='Physical screenshot and new phone-generated PNG/WAV; existing video is linked, not regenerated',
        privacy_reviewed=True,private_endpoints_published=False,api_keys_published=False,
        screenshot=raw['media'],quality_accepted=False,files=files)
    (MEDIA/'manifest.json').write_text(json.dumps(media,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    PUBLIC.parent.mkdir(parents=True,exist_ok=True)
    PUBLIC.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return check()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',help='Completed build/device-lan-http/.../report.json')
    args=parser.parse_args()
    print(json.dumps(export(args.report) if args.report else check(),ensure_ascii=False))
