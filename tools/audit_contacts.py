"""Correlate actual Gazebo contact events with requested shots; no official score."""
import argparse
import json
from pathlib import Path
import re
from record_contacts import load_contact_entries

p=argparse.ArgumentParser()
p.add_argument('trial',type=Path)
a=p.parse_args()
logs=list((a.trial/'mission').glob('*/events.jsonl'))
if len(logs)!=1: raise ValueError('Expected exactly one mission')
events=[json.loads(s) for s in logs[0].read_text(encoding='utf-8').splitlines()]
expected={e['point']:e['marker'] for e in events if e['event']=='aim_aligned'}
shots={e['bullet']:{'point':e['point'],'expected_marker':expected[e['point']], 'target_contact':None}
       for e in events if e['event']=='bullet_spawn_observed'}
for entry in load_contact_entries(a.trial):
    names=entry['collisions']
    for bullet,item in shots.items():
        if item['target_contact'] or not any(n.startswith(bullet+'::') for n in names): continue
        targets=[n for n in names if n.startswith('target_')]
        if not targets: continue
        collision=targets[0]
        match=re.search(r'target_wheel::link::leaf_(\d+)_collision',collision)
        item['target_contact']={'collision':collision,'wheel_marker':int(match[1])+1 if match else None,
                                'source':entry['source'],
                                'raw_contact':entry['raw_contact']}
        item['expected_target_model']={1:'target_fixed',2:'target_wheel',3:'target_moving_3',4:'target_moving_4'}[item['point']]
        item['correct_model']=collision.startswith(item['expected_target_model']+'::')
        if match: item['correct_wheel_marker']=int(match[1])+1==item['expected_marker']
output={'run':events[-1]['run'],'complete':events[-1].get('complete',False),'shots':shots,
        'official_score':None,'interpretation':'Actual native Gazebo contact messages. Moving-board collision is shared by all three printed IDs, so contact alone does not prove the official scoring region.'}
(a.trial/'contact-evidence.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in output.items() if k!='shots'},indent=2))
for bullet,item in shots.items():
    print(bullet,item['point'],None if item['target_contact'] is None else item['target_contact']['collision'])
