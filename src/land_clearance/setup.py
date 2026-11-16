from glob import glob
from setuptools import setup

setup(
    name='land_clearance', version='0.1.0', packages=['land_clearance'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/land_clearance']),
        ('share/land_clearance', ['package.xml']),
        ('share/land_clearance/launch', glob('launch/*.py')),
        ('share/land_clearance/config', glob('config/*.yaml')),
        ('share/land_clearance/maps', glob('maps/*')),
        ('share/land_clearance/assets/point_targets', glob('assets/point_targets/*')),
        ('share/land_clearance/assets/markers', glob('assets/markers/*')),
        ('share/land_clearance/assets', ['assets/PROVENANCE.md']),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Competition team', maintainer_email='noreply@example.invalid',
    description='Camera-based land clearance mission', license='Proprietary',
    entry_points={'console_scripts': ['velocity_gate = land_clearance.velocity_gate:main',
                                     'mission = land_clearance.mission_node:main']},
)
