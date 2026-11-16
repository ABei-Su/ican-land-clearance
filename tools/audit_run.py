"""Offline geometric evidence only. Never imported by the mission controller."""
import argparse
import json
import math
from pathlib import Path


def local_point(point, model):
    x,y,z,w = model[3:]
    # Inverse unit-quaternion rotation.
    u = (-x,-y,-z)
    v = [point[i]-model[i] for i in range(3)]
    cross = lambda a,b: (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    t = [2*k for k in cross(u,v)]
    c = cross(u,t)
    return [v[i]+w*t[i]+c[i] for i in range(3)]


def box_distance(point, center, half):
    return math.sqrt(sum(max(0.,abs(point[i]-center[i])-half[i])**2 for i in range(3)))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('trial',type=Path)
    args=parser.parse_args()
    paths=list((args.trial/'mission').glob('*/events.jsonl'))
    if len(paths)!=1: raise ValueError('Expected one mission')
    events=[json.loads(x) for x in paths[0].read_text(encoding='utf-8').splitlines()]
    shots={e['bullet']:{'point':e['point'],'spawn_time':e['time']} for e in events if e['event']=='bullet_spawn_observed'}
    expected={e['point']:e['marker'] for e in events if e['event']=='aim_aligned'}
    leaves=[(0,0,.09),(0,.085595,.027812),(0,.052901,-.072812),(0,-.052901,-.072812),(0,-.085595,.027812)]
    for line in (args.trial/'recording/simulator-observations.jsonl').open():
        sample=json.loads(line); models=sample['models']
        for bullet,result in shots.items():
            if bullet not in models or 'first_sampled_contact' in result: continue
            p=models[bullet][:3]
            options=[]
            for name,model in models.items():
                if name=='target_fixed':
                    q=local_point(p,model)
                    options.append((box_distance(q,(0,0,0),(.01,.135,.135)),name,0,q))
                elif name=='target_wheel':
                    q=local_point(p,model)
                    for idx,center in enumerate(leaves):
                        options.append((box_distance(q,center,(.005,.025,.025)),name,idx+1,q))
                elif name in ('target_moving_3','target_moving_4'):
                    q=local_point(p,model)
                    options.append((box_distance(q,(0,0,0),(.01,.09,.035)),name,None,q))
            distance,name,marker,local=min(options)
            if distance < result.get('minimum_distance',math.inf):
                result.update(minimum_distance=distance, nearest_model=name)
            if distance<=.024:
                result['first_sampled_contact']={'model':name,'wheel_marker':marker,
                    'local_position':local,'distance_to_box':distance,'wall_time':sample['wall_time']}
    result={'run':events[-1]['run'],'complete':events[-1].get('complete',False),
            'maximum_speed':events[-1].get('maximum_speed'), 'shots':shots,
            'expected_markers':expected,
            'interpretation':'Sampled sphere-to-box distance <= 0.024 m (bullet radius 0.020 m plus 0.004 m numerical allowance). This is local geometric evidence, not official hit/score. Moving-board subregion is not inferred.',
            'official_score':None}
    target=args.trial/'offline-evidence.json'
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
