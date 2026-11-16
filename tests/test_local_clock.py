"""Clock isolation restores the service after every supported exit path."""
import subprocess
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from clock_safe_trial import run_with_clock_guard


class LocalClockTests(unittest.TestCase):
    def exercise(self, state='active', failure=None):
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            if command[:2] == ['systemctl', 'show']:
                return subprocess.CompletedProcess(command, 0, stdout=state+'\n')
            if command == ['trial'] and failure:
                raise failure
            return subprocess.CompletedProcess(command, 7 if command == ['trial'] else 0)

        return calls, run

    def test_active_service_restored_and_trial_exit_propagated(self):
        calls, run = self.exercise()
        self.assertEqual(run_with_clock_guard(['trial'], run), 7)
        self.assertEqual([c[:2] for c in calls],
                         [['systemctl', 'show'], ['systemctl', 'stop'], ['trial'], ['systemctl', 'start']])

    def test_inactive_service_is_left_inactive(self):
        calls, run = self.exercise('inactive')
        self.assertEqual(run_with_clock_guard(['trial'], run), 7)
        self.assertEqual(len(calls), 2)

    def test_launch_failure_still_restores(self):
        calls, run = self.exercise(failure=OSError('launch failed'))
        with self.assertRaises(OSError):
            run_with_clock_guard(['trial'], run)
        self.assertEqual(calls[-1], ['systemctl', 'start', 'systemd-timesyncd'])

    def test_interrupt_still_restores(self):
        calls, run = self.exercise(failure=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            run_with_clock_guard(['trial'], run)
        self.assertEqual(calls[-1], ['systemctl', 'start', 'systemd-timesyncd'])

    def test_transitional_service_state_rejects_before_launch(self):
        calls, run = self.exercise('activating')
        with self.assertRaises(RuntimeError):
            run_with_clock_guard(['trial'], run)
        self.assertEqual(len(calls), 1)

    def test_stop_failure_prevents_trial_and_attempts_restore(self):
        calls, base = self.exercise()

        def run(command, **kwargs):
            result = base(command, **kwargs)
            if command[:2] == ['systemctl', 'stop']:
                raise subprocess.CalledProcessError(1, command)
            return result

        with self.assertRaises(subprocess.CalledProcessError):
            run_with_clock_guard(['trial'], run)
        self.assertNotIn(['trial'], calls)
        self.assertEqual(calls[-1], ['systemctl', 'start', 'systemd-timesyncd'])

    def test_restoration_failure_is_reported(self):
        calls, base = self.exercise()

        def run(command, **kwargs):
            result = base(command, **kwargs)
            if command[:2] == ['systemctl', 'start']:
                raise subprocess.CalledProcessError(1, command)
            return result

        with self.assertRaises(subprocess.CalledProcessError):
            run_with_clock_guard(['trial'], run)
        self.assertIn(['trial'], calls)
