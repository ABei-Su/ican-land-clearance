"""Run the actual Bash entry point with inert ROS/build commands."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'posix', 'Requires Bash/POSIX launcher')
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.workspace = self.base/'workspace with spaces'
        (self.workspace/'src/land_clearance').mkdir(parents=True)
        self.stub = self.base/'stub'
        self.stub.mkdir()
        ros = self.stub/'ros2'
        ros.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
                       'case "$*" in\n'
                       '"launch land_clearance navigation.launch.py"|"run land_clearance mission --ros-args -p enable_shoot:=true") exit 0;;\n'
                       '*) exit 9;; esac\n')
        ros.chmod(0o755)
        self.setup = self.base/'inert-setup.sh'
        self.setup.write_text('source() { case "$1" in /opt/*) return 0;; esac; '
                              '[[ -f "$1" ]] || { echo "Missing overlay: $1" >&2; return 1; }; }\n'
                              'colcon() { printf "%s\\n" "$PWD" > "$BUILD_LOG"; '
                              'mkdir -p install; touch install/setup.bash; }\n')
        self.env = dict(os.environ, BASH_ENV=str(self.setup),
                        PATH=str(self.stub)+':'+os.environ['PATH'],
                        CALL_LOG=str(self.base/'calls'), BUILD_LOG=str(self.base/'build'))
        self.env.pop('ICAN_WORKSPACE', None)

    def launch(self, directory, override=None):
        directory.mkdir(exist_ok=True)
        script = directory/'run.sh'
        script.write_bytes((Path(__file__).resolve().parents[1]/'run.sh').read_bytes())
        if override is not None:
            self.env['ICAN_WORKSPACE'] = str(override)
        return subprocess.run(['bash', str(script)], cwd=self.base, env=self.env,
                              capture_output=True, text=True, timeout=10)

    def assert_started(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.base/'build').read_text().strip(), str(self.workspace))
        self.assertIn('run land_clearance mission', (self.base/'calls').read_text())

    def test_root_script_independent_of_cwd(self):
        self.assert_started(self.launch(self.workspace))

    def test_official_scripts_subdirectory(self):
        self.assert_started(self.launch(self.workspace/'scripts'))

    def test_explicit_workspace_for_separate_script(self):
        self.assert_started(self.launch(self.base/'upload', self.workspace))

    def test_relative_workspace_loads_built_overlay(self):
        self.assert_started(self.launch(self.base/'upload', self.workspace.name))

    def test_missing_workspace_stops_before_build(self):
        result = self.launch(self.base/'upload')
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.base/'build').exists())

    def test_invalid_override_does_not_fall_back(self):
        result = self.launch(self.workspace, self.base/'missing')
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.base/'build').exists())
