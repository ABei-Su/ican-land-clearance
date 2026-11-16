"""Run the rehearsal script with inert child processes and a temporary archive."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import submission_integrity


class RehearsalExitTests(unittest.TestCase):
    def execute(self, code=None, timeout=False):
        source = Path(__file__).resolve().parents[1]/'tools/audit_platform_trial.py'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('tools', 'deliverables', 'reports', 'workspace'):
                (root/name).mkdir()
            script = root/'tools/audit_platform_trial.py'
            script.write_bytes(source.read_bytes())
            with zipfile.ZipFile(root/'deliverables/src.zip', 'w') as archive:
                archive.writestr('src/example.txt', 'fixture')
            (root/'deliverables/run.sh').write_text('# inert fixture\n')
            simulation = Mock()
            simulation.poll.return_value = 0
            simulation.wait.return_value = 0
            mission = Mock()
            mission.poll.return_value = 0
            mission.wait.side_effect = [subprocess.TimeoutExpired('mission', 480), 0] if timeout else [code, code]
            with patch.object(submission_integrity, 'validate_submission'), \
                 patch('subprocess.run', return_value=Mock(returncode=1)), \
                 patch('subprocess.Popen', side_effect=[simulation, mission]), \
                 patch('tempfile.mkdtemp', return_value=str(root/'workspace')), \
                 contextlib.redirect_stdout(io.StringIO()):
                try:
                    runpy.run_path(str(script), run_name='__main__')
                except SystemExit as exc:
                    status = exc.code
                else:
                    status = 0
            reports = list((root/'reports').glob('*/rehearsal.json'))
            self.assertEqual(len(reports), 1, 'Result must survive failure')
            return status, json.loads(reports[0].read_text())

    def test_success(self):
        self.assertEqual(self.execute(0)[0], 0)

    def test_child_failure(self):
        status, result = self.execute(7)
        self.assertEqual(status, 7)
        self.assertEqual(result['exit_code'], 7)

    def test_child_signal(self):
        self.assertEqual(self.execute(-15)[0], 143)

    def test_timeout(self):
        status, result = self.execute(timeout=True)
        self.assertEqual(status, 124)
        self.assertEqual(result['timeout_seconds'], 480)
