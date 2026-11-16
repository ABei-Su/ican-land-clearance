"""Local-only scene fixture: change ground textures in a copy, never physics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil

p=argparse.ArgumentParser()
p.add_argument('seed',type=int)
a=p.parse_args()
source=Path('/opt/ican_shoot_sim/share/ican_land_sim')
dest=Path.home()/'contest-scenarios'/f'seed-{a.seed}'
if dest.exists(): raise SystemExit('Scenario already exists; refusing overwrite')
share=dest/'share/ican_land_sim'
shutil.copytree(source,share)
(dest/'share/ament_index/resource_index/packages').mkdir(parents=True)
(dest/'share/ament_index/resource_index/packages/ican_land_sim').touch()
os.symlink('/opt/ican_shoot_sim/lib',dest/'lib',target_is_directory=True)
material=share/'materials/scripts/ican_land.material'
text=material.read_text()
templates=sorted(p.name for p in (share/'materials/textures/point_targets').glob('*') if p.suffix.lower() in ('.png','.jpg','.jpeg'))
if not templates:
    templates=sorted(p.name for p in (share/'materials/textures').rglob('*') if any(p.name.startswith(x+'_') for x in ('collapsed_ruins','landslide','trapped_people','damaged_vehicle','rescue_camp')))
if len(templates)!=10: raise ValueError(f'Expected 10 public templates, got {templates}')
choices=random.Random(a.seed).sample(templates,5)
for i,name in enumerate(choices):
    pattern=r'(material ShootingGroundTarget'+str(i)+r'\b.*?\btexture\s+)(\S+)'
    text,count=re.subn(pattern,lambda m:m[1]+name,text,count=1,flags=re.S)
    if count!=1: raise ValueError('Ground material missing')
material.write_text(text)
hashes={}
for original in source.rglob('*'):
    if original.is_file() and original.relative_to(source).as_posix()!='materials/scripts/ican_land.material':
        copied=share/original.relative_to(source)
        digest=hashlib.sha256(original.read_bytes()).hexdigest()
        if hashlib.sha256(copied.read_bytes()).hexdigest()!=digest: raise ValueError('Non-texture content changed')
        hashes[original.relative_to(source).as_posix()]=digest
(dest/'fixture-manifest.json').write_text(json.dumps({'seed':a.seed,'ground_textures':choices,'unchanged_files':hashes},indent=2))
print(dest)
