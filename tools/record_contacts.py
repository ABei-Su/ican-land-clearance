"""Independent Gazebo transport observer. No ROS commands or model changes."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time


def load_contact_entries(directory):
    records=[]
    for name in ('contacts.jsonl','contacts-live.jsonl'):
        path=Path(directory)/name
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                item=json.loads(line)
                item['source']=name
                records.append(item)
    records.sort(key=lambda item:item['wall_time'])
    seen=set()
    result=[]
    for item in records:
        key=(item['wall_time'],tuple(sorted(item['collisions'])))
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def contact_blocks(lines):
    block=[]
    depth=0
    for line in lines:
        if not block and line.strip()!='contact {':
            continue
        block.append(line)
        depth+=line.count('{')-line.count('}')
        if depth==0:
            text=''.join(block)
            if 'bullet_' in text:
                yield text
            block=[]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    deadline=time.monotonic()+60
    while True:
        try:
            listing=subprocess.run(['gz','topic','-l'],capture_output=True,text=True,timeout=3)
            if '/gazebo/default/physics/contacts' in listing.stdout.splitlines():
                break
        except subprocess.TimeoutExpired:
            pass
        if time.monotonic()>=deadline:
            raise TimeoutError('Gazebo contact transport not available')
        time.sleep(.5)
    process=subprocess.Popen(['gz','topic','-e','/gazebo/default/physics/contacts'],
                             stdout=subprocess.PIPE,text=True,bufsize=1)
    seen=set()
    try:
        with args.output.open('x',encoding='utf-8',buffering=1) as output:
            for block in contact_blocks(process.stdout):
                names=re.findall(r'collision[12]: "([^"]+)"',block)
                if len(names)!=2:
                    continue
                pair=tuple(sorted(names))
                if pair in seen:
                    continue
                seen.add(pair)
                output.write(json.dumps({'wall_time':time.monotonic(),'collisions':names,
                                        'raw_contact':block,'official_score':None})+'\n')
    except KeyboardInterrupt:
        pass
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__=='__main__': main()
