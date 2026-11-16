"""Own one fresh local simulation trial and clean up only its process groups."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from process_control import terminate_as_interrupt

p = argparse.ArgumentParser()
p.add_argument('directory')
p.add_argument('--scenario-prefix', type=Path)
a = p.parse_args()
out = Path(a.directory).resolve()
out.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[1]
children = []
logs = []


def start(name, command, env=None):
    log = (out / (name+'.log')).open('w')
    logs.append(log)
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=True, env=env)
    children.append(process)
    return process


signal.signal(signal.SIGTERM, terminate_as_interrupt)
try:
    sim_env = os.environ.copy()
    if a.scenario_prefix:
        prefix = a.scenario_prefix.resolve(strict=True)
        sim_env['AMENT_PREFIX_PATH'] = str(prefix)+':'+sim_env.get('AMENT_PREFIX_PATH','')
    start('simulation', ['ros2', 'launch', 'ican_shoot_sim', 'sim.launch.py'], sim_env)
    start('contacts', [sys.executable, str(root/'tools/record_contacts.py'), str(out/'contacts.jsonl')])
    start('navigation', ['ros2', 'launch', 'land_clearance', 'navigation.launch.py'])
    recorder = start('recorder', [sys.executable, str(root/'tools/record_run.py'), str(out/'recording')])
    mission = start('mission', [sys.executable, str(root/'tools/run_mission_local.py'), '--ros-args',
                               '-p', 'enable_shoot:=true', '-p', 'ready_timeout:=90.0',
                               '-p', 'output_dir:='+str(out/'mission')])
    result = mission.wait(timeout=900)
    try:
        recorder.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    print('Mission exit:', result, 'Evidence:', out, flush=True)
finally:
    for child in reversed(children):
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGINT)
    for child in reversed(children):
        try:
            child.wait(timeout=12)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
    for log in logs:
        log.close()
sys.exit(result)
