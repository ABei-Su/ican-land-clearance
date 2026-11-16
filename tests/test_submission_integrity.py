import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from submission_integrity import validate_submission


class SubmissionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'src/land_clearance/node.py'
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b'current source\n')
        (self.root/'run.sh').write_bytes(b'#!/bin/bash\n')
        self.out = self.root/'deliverables'
        self.out.mkdir()
        (self.out/'run.sh').write_bytes((self.root/'run.sh').read_bytes())
        self.write_archive([('src/land_clearance/node.py', b'current source\n')])

    def write_archive(self, entries):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.out/'src.zip', 'w') as archive:
                for name, content in entries:
                    archive.writestr(name, content)

    def test_current_archive_passes(self):
        self.assertEqual(validate_submission(self.root), 1)

    def test_stale_source_is_rejected(self):
        self.source.write_bytes(b'new source\n')
        with self.assertRaisesRegex(ValueError, 'content'):
            validate_submission(self.root)

    def test_stale_launcher_is_rejected(self):
        (self.out/'run.sh').write_bytes(b'old launcher')
        with self.assertRaisesRegex(ValueError, 'run.sh'):
            validate_submission(self.root)

    def test_missing_and_unexpected_members_are_rejected(self):
        for entries in ([], [('src/land_clearance/extra.py', b'other')]):
            with self.subTest(entries=entries):
                self.write_archive(entries)
                with self.assertRaisesRegex(ValueError, 'members'):
                    validate_submission(self.root)

    def test_unsafe_and_duplicate_paths_are_rejected(self):
        paths = ['src/land_clearance/../outside.py', '/src/land_clearance/node.py',
                 'src/land_clearance/./node.py', 'src\\land_clearance\\node.py']
        for name in paths:
            with self.subTest(name=name):
                self.write_archive([(name, b'data')])
                with self.assertRaisesRegex(ValueError, 'path'):
                    validate_submission(self.root)
        self.write_archive([('src/land_clearance/node.py', b'current source\n')]*2)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_submission(self.root)

    def test_archive_symlink_is_rejected(self):
        info = zipfile.ZipInfo('src/land_clearance/node.py')
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        self.write_archive([(info, b'/outside')])
        with self.assertRaisesRegex(ValueError, 'symlink'):
            validate_submission(self.root)
