"""Bounded cleanup for locally owned process groups."""
import os
import signal
import subprocess
import time
from pathlib import Path


def terminate_as_interrupt(signum, frame):
    # A second termination request must not interrupt the cleanup already begun.
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise KeyboardInterrupt('Local trial terminated')


def live_group(group):
    # Linux-only launcher: an exited leader does not imply its children exited.
    # Zombies have finished cleanup and may await reaping by their new parent.
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            fields = (entry/'stat').read_text().rsplit(')', 1)[1].split()
        except (FileNotFoundError, ProcessLookupError):
            continue
        if int(fields[2]) == group and fields[0] != 'Z':
            return True
    return False


def signal_group(group, sig):
    try:
        os.killpg(group, sig)
    except ProcessLookupError:
        pass  # The final member exited between inspection and signalling.


def run_owned(command):
    process = subprocess.Popen(command, start_new_session=True)
    try:
        return subprocess.CompletedProcess(command, process.wait())
    finally:
        if live_group(process.pid):
            signal_group(process.pid, signal.SIGTERM)
            # The trial supervisor owns separate simulator groups and can need
            # up to 60 seconds to drain them. Wait for it, not just runuser.
            deadline = time.monotonic() + 90
            while live_group(process.pid) and time.monotonic() < deadline:
                process.poll()
                time.sleep(.05)
            if live_group(process.pid):
                signal_group(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
                raise RuntimeError('Trial cleanup timed out; inspect simulator processes before restarting')
        process.wait(timeout=5)
