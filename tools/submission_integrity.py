"""Check the submission before extraction or final delivery."""
from pathlib import Path
import stat
import zipfile


def validate_submission(root):
    root = Path(root)
    allowed = {'.py', '.yaml', '.xml', '.cfg', '.png', '.jpg', '.pgm', '.md'}
    expected = {}
    for path in (root/'src').rglob('*'):
        if path.is_symlink():
            raise ValueError(f'Source symlink: {path}')
        if not path.is_file() or '__pycache__' in path.parts:
            continue
        if path.suffix in allowed or (path.name == 'land_clearance' and path.parent.name == 'resource'):
            expected[path.relative_to(root).as_posix()] = path
    if not expected:
        raise ValueError('No source members found')
    with zipfile.ZipFile(root/'deliverables/src.zip') as archive:
        seen = set()
        for item in archive.infolist():
            name = item.filename
            if (not name.startswith('src/land_clearance/') or '\\' in name
                    or any(part in ('', '.', '..') or ':' in part for part in name.split('/'))):
                raise ValueError(f'Invalid archive path: {name}')
            if name in seen:
                raise ValueError(f'Archive duplicate: {name}')
            seen.add(name)
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError(f'Archive symlink: {name}')
        if seen != expected.keys():
            raise ValueError(f'Archive members differ: missing={sorted(expected.keys()-seen)}, unexpected={sorted(seen-expected.keys())}')
        for name, path in expected.items():
            if archive.read(name) != path.read_bytes():
                raise ValueError(f'Archive content differs from source: {name}')
    if (root/'run.sh').read_bytes() != (root/'deliverables/run.sh').read_bytes():
        raise ValueError('Delivered run.sh differs from current launcher')
    return len(expected)
