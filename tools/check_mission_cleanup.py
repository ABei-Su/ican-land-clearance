"""Fault-inject the real run method without ROS nodes, navigation or shooting."""
import io
from types import SimpleNamespace
from unittest.mock import Mock, patch
from land_clearance.core import Mission, Phase
from land_clearance.mission_node import MissionNode


for cancel_fails in (False, True):
    events = []
    stream = io.StringIO()
    cancel = Mock(return_value=object())
    node = SimpleNamespace(
        core=Mission(), mode='nav', max_speed=.2, logfile=stream,
        get_parameter=lambda name: SimpleNamespace(value=1.),
        wait=Mock(side_effect=RuntimeError('primary sensor failure')),
        heartbeat=Mock(), nav_goal=SimpleNamespace(cancel_goal_async=cancel),
        log=lambda event, **data: events.append((event, data)))
    with patch('land_clearance.mission_node.rclpy.spin_once',
               side_effect=RuntimeError('repeated sensor failure')) as spin, \
         patch('land_clearance.mission_node.rclpy.spin_until_future_complete',
               side_effect=RuntimeError('cancel callback failure') if cancel_fails else None):
        assert MissionNode.run(node) is False
    assert node.core.phase == Phase.ABORTED and node.mode == 'stop'
    cancel.assert_called_once()
    assert spin.call_count == 5, 'Cleanup stopped before bounded stop attempts finished'
    assert node.heartbeat.call_count == 6
    assert events[0] == ('aborted', {'error': 'primary sensor failure'})
    failures = [data for event, data in events if event == 'cleanup_error']
    assert len(failures) == 5 + int(cancel_fails)
    assert events[-1] == ('run_ended', {'maximum_speed': .2, 'complete': False})
    assert stream.closed
print('PASS: repeated callback/cancel failures preserve abort, bounded stop attempts and log closure')
