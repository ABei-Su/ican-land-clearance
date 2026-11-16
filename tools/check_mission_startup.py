"""ROS adapter constructor regression in an isolated domain, without motion."""
import os
import tempfile
import time
from unittest.mock import patch
import rclpy
from land_clearance.mission_node import MissionNode
from land_clearance.core import Phase

if os.environ.get('ROS_DOMAIN_ID') != '71':
    raise SystemExit('Use isolated ROS_DOMAIN_ID=71')
with tempfile.TemporaryDirectory(prefix='ican-adapter-') as output:
    rclpy.init(args=['--ros-args', '-p', 'output_dir:='+output, '-p', 'ready_timeout:=0.25'])
    node = MissionNode()
    try:
        assert node.core.phase == Phase.INIT
        assert node.mode == 'stop'
        assert node.nav_goal is None
        assert not node.get_parameter('enable_shoot').value
        node.set_parameters([rclpy.parameter.Parameter('enable_shoot', value=True)])
        node.odom_at = time.monotonic()-1.
        node.aligned_at = time.monotonic()
        node.aligned_stamp = node.sim_now()
        with patch.object(node.shooter, 'call_async') as service:
            try:
                node.fire()
            except RuntimeError as exc:
                assert 'stale alignment/odometry' in str(exc)
            else:
                raise AssertionError('Stale odometry allowed firing')
            service.assert_not_called()
        assert node.run() is False
        assert node.core.phase == Phase.ABORTED
        import json
        errors = [json.loads(line).get('error', '') for line in (node.out/'events.jsonl').read_text().splitlines()]
        assert any('camera_image' in error and 'clock' in error for error in errors)
        assert not node.shots
        assert node.mode == 'stop'
        print('PASS: stopped startup; unavailable runtime aborts without firing')
    finally:
        node.logfile.close()
        node.destroy_node()
        rclpy.shutdown()
