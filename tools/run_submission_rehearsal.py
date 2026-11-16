"""Fixed local-only rehearsal wrapper; uses existing lock and clock restoration."""
import fcntl
import os
from pathlib import Path
import signal
from clock_safe_trial import run_with_clock_guard
from process_control import run_owned, terminate_as_interrupt

if os.geteuid() != 0:
    raise SystemExit('This local WSL wrapper requires root to restore clock service state.')
signal.signal(signal.SIGTERM, terminate_as_interrupt)
with open('/run/lock/ican-local-trial.lock', 'w') as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Another local trial is already running.')
    result = run_with_clock_guard([
        'runuser', '-u', 'ican', '--', 'python3',
        str(Path(__file__).with_name('audit_platform_trial.py'))], trial_run=run_owned)
    raise SystemExit(result)
