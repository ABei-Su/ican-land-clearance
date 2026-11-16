"""Build an auditable source-only archive, excluding local data and caches."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

root = Path(__file__).resolve().parents[1]
out = root / 'deliverables'
out.mkdir(exist_ok=True)
allowed = {'.py', '.yaml', '.xml', '.cfg', '.png', '.jpg', '.pgm', '.md'}
files = []
for path in sorted((root/'src').rglob('*')):
    if path.is_symlink():
        raise ValueError(f'Unexpected source symlink: {path}')
    if not path.is_file() or '__pycache__' in path.parts:
        continue
    if path.suffix in allowed or path.name == 'land_clearance' and path.parent.name == 'resource':
        files.append(path)
archive = out/'src.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for path in files:
        z.write(path, path.relative_to(root).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert 'src/land_clearance/package.xml' in z.namelist()
    assert 'src/land_clearance/maps/land_shoot_map.pgm' in z.namelist(), 'Navigation map missing'
    assert all(name.startswith('src/land_clearance/') and '..' not in Path(name).parts for name in z.namelist())
if archive.stat().st_size >= 20_000_000:
    raise ValueError('Source archive exceeds conservative 20 MB upload limit')
shutil.copyfile(root/'run.sh', out/'run.sh')
manifest = {'status':'three local mission layouts completed; official platform compatibility and scoring unverified',
            'files': {p.name:{'bytes':p.stat().st_size, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in (archive,out/'run.sh')}, 'source_file_count':len(files)}
(out/'code-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
