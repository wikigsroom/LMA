"""Check actual host PNG attribution and explicitly failed-gate still media."""
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image
from evidence import current


def check(records, root):
    directory = root / 'docs/media/development'
    media = json.loads((directory / 'lcm-preparation-media.json').read_text(encoding='utf-8'))
    current(media['input_fingerprint'])
    assert media['kind'] == 'actual_trained_host_png_outputs' and media['original_pngs_copied_without_reencoding']
    assert not any(media[k] for k in ['physical_android','app_screen_recording','semantic_quality_accepted','complete_release_accepted','image_comparison_gate_passed'])
    assert media['slideshow_frames'] == 2 and media['gif_duration_ms'] == 4800
    assert media['mp4_frames'] == 48 and media['mp4_fps'] == 10
    names = {'lcm-preparation-original-bias-control.png','lcm-preparation-native-prepared.png',
             'lcm-preparation-contact-sheet.png','lcm-preparation-slideshow.gif','lcm-preparation-slideshow.mp4'}
    assert set(media['files']) == names
    for name, identity in media['files'].items():
        data = (directory / name).read_bytes()
        assert len(data) == identity['bytes'] and hashlib.sha256(data).hexdigest() == identity['sha256']
    jobs = {j['name']:j for j in records['lcm-overlay-trained.json']['jobs']}
    for name in ['original-bias-control','native-prepared']:
        assert media['source_pngs'][name] == jobs[name]['image']['sha256']
        assert media['files']['lcm-preparation-'+name+'.png']['sha256'] == jobs[name]['image']['sha256']
        with Image.open(directory / ('lcm-preparation-'+name+'.png')) as image:
            assert image.size == (512,512) and image.format == 'PNG'
    with Image.open(directory / 'lcm-preparation-contact-sheet.png') as image: assert image.size == (1056,746)
    with Image.open(directory / 'lcm-preparation-slideshow.gif') as image:
        assert image.n_frames == 2 and image.size == (1000,800)
        durations = []
        for index in range(image.n_frames): image.seek(index);durations.append(image.info['duration'])
        assert durations == [2400,2400]
    result = subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries',
        'stream=width,height,nb_read_frames,avg_frame_rate,duration','-of','json',str(directory/'lcm-preparation-slideshow.mp4')],
        capture_output=True,check=True,timeout=30)
    video=json.loads(result.stdout)['streams'][0]
    assert video['width']==1000 and video['height']==800 and video['nb_read_frames']=='48'
    assert video['avg_frame_rate']=='10/1' and float(video['duration'])==4.8


if __name__ == '__main__':
    root=Path(__file__).resolve().parents[1]
    record=json.loads((root/'verification/development/lcm-overlay-trained.json').read_text(encoding='utf-8'))
    check({'lcm-overlay-trained.json':record},root)
    print('Five actual HOST media files verified; failed pixel gate and non-Android scope retained.')
