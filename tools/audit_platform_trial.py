"""Local submission rehearsal. No remote requests or official evaluation."""
import json
from datetime import datetime
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import zipfile
from submission_integrity import validate_submission

root = Path(__file__).resolve().parents[1]
out = root/'reports'/datetime.now().strftime('submission-rehearsal-%Y%m%d-%H%M%S')
out.mkdir(exist_ok=True)
validate_submission(root)
if subprocess.run(['pgrep', '-x', 'gzserver'], capture_output=True).returncode == 0:
    raise SystemExit('Existing simulator must finish first')
workspace = Path(tempfile.mkdtemp(prefix='ican-official-rehearsal-'))
with zipfile.ZipFile(root/'deliverables/src.zip') as archive:
    archive.extractall(workspace)
(workspace/'run.sh').write_bytes((root/'deliverables/run.sh').read_bytes())
env = {'HOME':str(workspace), 'USER':'ican', 'PATH':'/usr/local/bin:/usr/bin:/bin',
       'LANG':'C.UTF-8'}
for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR'):
    if name in os.environ:
        env[name] = os.environ[name]
setup = 'source /opt/ros/humble/setup.bash; source /opt/ican_shoot_sim/setup.bash; '
processes = []
handles = []
result = {'workspace':str(workspace), 'environment':env, 'official_upload':False}
try:
    for name, command in [('simulation',setup+'exec ros2 launch ican_shoot_sim sim.launch.py gui:=false'),
                          ('submission','exec bash ./run.sh')]:
        handle = (out/(name+'.log')).open('w')
        handles.append(handle)
        processes.append(subprocess.Popen(['bash','--noprofile','--norc','-c',command],
            cwd=workspace, env=env, stdout=handle, stderr=subprocess.STDOUT,
            start_new_session=True))
    result['exit_code'] = processes[-1].wait(timeout=480)
except subprocess.TimeoutExpired:
    result['timeout_seconds'] = 480
finally:
    for process in reversed(processes):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
    for handle in handles:
        handle.close()
    result['mission_logs'] = []
    for path in (workspace/'land-runs').glob('*/events.jsonl'):
        destination = out/(path.parent.name+'-events.jsonl')
        destination.write_bytes(path.read_bytes())
        result['mission_logs'].append(destination.name)
    (out/'rehearsal.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
if 'timeout_seconds' in result:
    raise SystemExit(124)
code = result.get('exit_code', 1)
raise SystemExit(128 - code if code < 0 else code)
