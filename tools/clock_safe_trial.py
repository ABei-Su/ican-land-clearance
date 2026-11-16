"""Local-only Windows/WSL clock isolation; never part of the submission."""
import os
import subprocess


def run_with_clock_guard(command, run=subprocess.run, trial_run=None):
    state = run(['systemctl', 'show', '--property=ActiveState', '--value',
                 'systemd-timesyncd'], check=True, capture_output=True,
                text=True, timeout=10).stdout.strip()
    if state not in ('active', 'inactive', 'failed'):
        raise RuntimeError(f'Time synchronization is transitioning: {state}')
    active = state == 'active'
    try:
        if active:
            run(['systemctl', 'stop', 'systemd-timesyncd'], check=True, timeout=15)
        return (trial_run or run)(command).returncode
    finally:
        if active:
            run(['systemctl', 'start', 'systemd-timesyncd'], check=True, timeout=15)


def main():
    import fcntl
    import sys
    import signal
    from process_control import run_owned, terminate_as_interrupt

    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise SystemExit('Use the fixed Windows 05-run-full-mission.cmd launcher.')
    signal.signal(signal.SIGTERM, terminate_as_interrupt)
    # Prevent two wrappers from restoring each other's temporary service state.
    with open('/run/lock/ican-local-trial.lock', 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another iCAN local trial is already running.')
        print('Local trial: temporarily pause Linux time synchronization; restore on exit.',
              flush=True)
        result = run_with_clock_guard([
            'runuser', '-u', 'ican', '--', 'bash',
            '/mnt/e/ican/contest_ws/scripts/run-local-demo.sh'], trial_run=run_owned)
        print('Local trial finished; prior time synchronization state restored.', flush=True)
        raise SystemExit(result)


if __name__ == '__main__':
    main()
