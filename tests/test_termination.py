import os
from pathlib import Path
import subprocess
import sys
import unittest


@unittest.skipUnless(os.name == 'posix', 'Requires POSIX SIGTERM semantics')
class TerminationTests(unittest.TestCase):
    def test_group_cleanup_finishes_before_clock_restore(self):
        import signal
        import selectors
        import tempfile
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            marker = str(Path(directory)/'cleaned')
            worker = (
                "import signal,time,pathlib,sys\n"
                "def stop(*args):\n"
                " time.sleep(.5)\n"
                f" pathlib.Path({marker!r}).write_text('done')\n"
                " sys.exit(0)\n"
                "signal.signal(signal.SIGTERM,stop)\n"
                "print('ready',flush=True)\n"
                "time.sleep(30)\n"
            )
            leader = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{worker!r}]); time.sleep(30)"
            outer = (
                "import signal,sys,pathlib\n"
                "from process_control import run_owned,terminate_as_interrupt\n"
                "signal.signal(signal.SIGTERM,terminate_as_interrupt)\n"
                "try:\n"
                f" run_owned([sys.executable,'-c',{leader!r}])\n"
                "finally:\n"
                f" print('restore_after_cleanup='+str(pathlib.Path({marker!r}).exists()),flush=True)\n"
            )
            env = dict(os.environ, PYTHONPATH=str(root/'tools'))
            with subprocess.Popen([sys.executable, '-c', outer], env=env, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(child.stdout, selectors.EVENT_READ)
                        self.assertTrue(selector.select(timeout=5))
                    self.assertEqual(child.stdout.readline().strip(), 'ready')
                    child.send_signal(signal.SIGTERM)
                    out, _ = child.communicate(timeout=8)
                    self.assertIn('restore_after_cleanup=True', out)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait()

    def test_sigterm_unwinds_cleanup_instead_of_abrupt_exit(self):
        import signal
        import selectors
        root = Path(__file__).resolve().parents[1]
        code = (
            "import signal,time\n"
            "from process_control import terminate_as_interrupt\n"
            "signal.signal(signal.SIGTERM,terminate_as_interrupt)\n"
            "try:\n"
            " print('ready',flush=True)\n"
            " time.sleep(30)\n"
            "finally:\n"
            " print('cleanup',flush=True)\n"
        )
        env = dict(os.environ, PYTHONPATH=str(root/'tools'))
        with subprocess.Popen([sys.executable, '-c', code], env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(child.stdout, selectors.EVENT_READ)
                    self.assertTrue(selector.select(timeout=5), 'Child readiness timeout')
                self.assertEqual(child.stdout.readline().strip(), 'ready')
                child.send_signal(signal.SIGTERM)
                out, _ = child.communicate(timeout=5)
                self.assertIn('cleanup', out)
                self.assertNotEqual(child.returncode, 0)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()
