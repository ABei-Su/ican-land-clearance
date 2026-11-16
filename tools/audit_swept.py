"""Supplement sampled evidence with segment proximity; NEVER call it a hit."""
import argparse
import json
from pathlib import Path
from audit_run import local_point
from trajectory_geometry import segment_box_distance

p=argparse.ArgumentParser()
p.add_argument('trial',type=Path)
a=p.parse_args()
logs=list((a.trial/'mission').glob('*/events.jsonl'))
if len(logs)!=1:
    raise ValueError('Expected exactly one mission log')
events=[json.loads(s) for s in logs[0].read_text(encoding='utf-8').splitlines()]
shots={e['bullet']:{'point':e['point'],'minimum_segment_distance':None} for e in events if e['event']=='bullet_spawn_observed'}
previous={}
leaves=[(0,0,.09),(0,.085595,.027812),(0,.052901,-.072812),(0,-.052901,-.072812),(0,-.085595,.027812)]
for line in (a.trial/'recording/simulator-observations.jsonl').open(encoding='utf-8'):
    sample=json.loads(line)
    for bullet,result in shots.items():
        if bullet not in sample['models']: continue
        old=previous.get(bullet)
        previous[bullet]=sample
        if old is None or not 0<sample['wall_time']-old['wall_time']<=.05: continue
        name={1:'target_fixed',2:'target_wheel',3:'target_moving_3',4:'target_moving_4'}[result['point']]
        if name not in old['models'] or name not in sample['models']: continue
        start=local_point(old['models'][bullet][:3],old['models'][name])
        end=local_point(sample['models'][bullet][:3],sample['models'][name])
        half=(.005,.025,.025) if result['point']==2 else ((.01,.135,.135) if result['point']==1 else (.01,.09,.035))
        centers=leaves if result['point']==2 else [(0,0,0)]
        for index,center in enumerate(centers):
            distance,point=segment_box_distance([start[i]-center[i] for i in range(3)], [end[i]-center[i] for i in range(3)],half)
            if result['minimum_segment_distance'] is None or distance<result['minimum_segment_distance']:
                result.update(minimum_segment_distance=distance,local_point=[point[i]+center[i] for i in range(3)],
                              wheel_leaf=index+1 if result['point']==2 else None,
                              sample_interval=sample['wall_time']-old['wall_time'])
output={'shots':shots,'interpretation':'Straight segments between <=50ms relative-pose samples. Nearness is interpolated geometric evidence only; collisions/target motion may bend the actual path. No hit or scoring-region verdict.', 'official_score':None}
(a.trial/'swept-evidence.json').write_text(json.dumps(output,indent=2))
print(json.dumps(output,indent=2))
