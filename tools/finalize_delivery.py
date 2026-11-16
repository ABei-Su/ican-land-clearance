"""Validate final submission formats and write file hashes without score claims."""
import hashlib
import json
from pathlib import Path
import subprocess
from pypdf import PdfReader
from docx import Document
import zipfile
import re
from submission_integrity import validate_submission

root=Path(__file__).resolve().parents[1]
out=root/'deliverables'
validate_submission(root)
files=['demo.mp4','technical-report.pdf','technical-report.docx','src.zip','run.sh']
limits=[50_000_000,20_000_000,20_000_000,20_000_000,1_000_000]
entries={}
for name,limit in zip(files,limits):
    path=out/name
    assert 0<path.stat().st_size<limit, name
    entries[name]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
assert len(PdfReader(out/'technical-report.pdf').pages)==6
assert '陆地障碍物清除任务' in '\n'.join(p.text for p in Document(out/'technical-report.docx').paragraphs)
assert b'\r' not in (out/'run.sh').read_bytes(), 'Linux script must have LF line endings'
with zipfile.ZipFile(out/'src.zip') as archive:
    assert archive.testzip() is None
    for item in archive.namelist():
        assert item.startswith('src/land_clearance/') and '..' not in Path(item).parts
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out/'demo.mp4')]))
video=probe['streams'][0]
assert video['codec_name']=='h264' and video['height']>=720
assert 180<=float(probe['format']['duration'])<=480
test_log=(root/'reports/final-tests.log').read_text(encoding='utf-8')
counts=re.findall(r'Ran (\d+) tests',test_log)
assert counts and test_log.rstrip().endswith('OK'), 'Fresh test log must show a successful complete suite'
completed=[]
for trial in ['trial-04','trial-seed17-v2','trial-seed29','trial-seed29-buffer-restored','trial-seed29-contacts','trial-clock-isolated-20261021','local-20261021-010554']:
    logs=list((root/'reports'/trial/'mission').glob('*/events.jsonl'))
    if len(logs)==1:
        last=json.loads(logs[0].read_text(encoding='utf-8').splitlines()[-1])
        if last.get('complete'): completed.append(last['run'])
manifest={'status':'Local deliverables prepared; no official upload or score',
    'files':entries,'video_seconds':float(probe['format']['duration']),'pdf_pages':6,
    'unit_tests':int(counts[-1]),'completed_local_runs':completed,
    'limitations':['Guide startup responsibilities confirmed; server runtime details and scoring unverified',
      'Latest video run has four native target contacts; moving-board scoring region unverified',
      'Earlier trials include unconfirmed contacts; arbitrary-layout reliability not established'],
    'verification':'../docs/verification.md'}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
