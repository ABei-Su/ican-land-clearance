"""Validate extracted submission assets and Python entry points on Linux."""
import pathlib
import subprocess
import tempfile
import zipfile
from submission_integrity import validate_submission

root=pathlib.Path(__file__).resolve().parents[1]
validate_submission(root)
with tempfile.TemporaryDirectory(prefix='ican-submission-') as temp:
    workspace=pathlib.Path(temp)
    with zipfile.ZipFile(root/'deliverables/src.zip') as archive:
        archive.extractall(workspace)
    subprocess.run(['bash','-n',str(root/'deliverables/run.sh')],check=True)
    subprocess.run(['colcon','build','--packages-select','land_clearance'],cwd=workspace,check=True)
    share=workspace/'install/land_clearance/share/land_clearance'
    assert (share/'maps/land_shoot_map.pgm').stat().st_size>0
    assert len(list((share/'assets/point_targets').glob('*')))==10
    # IDs 6-8 are decoded from the single public board.png.
    assert {p.name for p in (share/'assets/markers').glob('*')} == {'1.png','2.png','3.png','4.png','5.png','board.png'}
    assert (share/'launch/navigation.launch.py').is_file()
    probe = '''from pathlib import Path
from land_clearance import mission_node, velocity_gate
from land_clearance.mission_node import MissionNode
from land_clearance.velocity_gate import GateNode
for module in (mission_node, velocity_gate):
    assert Path(module.__file__).resolve().is_relative_to(Path.cwd()/'install'), module.__file__
'''
    subprocess.run(['bash','-c','source install/setup.bash && python3 -c "$1"',
                    'submission-probe',probe],cwd=workspace,check=True)
print('PASS: source equality, safe archive, clean build, assets and isolated ROS imports')
