"""Exercise the real ROS odometry callback without creating nodes or moving robots."""
import math
from types import SimpleNamespace
from unittest.mock import patch
from nav_msgs.msg import Odometry
from land_clearance.mission_node import MissionNode
from land_clearance.runtime_contract import leased_motion_mode


def message(x, y, angular):
    msg = Odometry()
    msg.twist.twist.linear.x = x
    msg.twist.twist.linear.y = y
    msg.twist.twist.angular.z = angular
    return msg


for axis in range(3):
    for value in (math.nan, math.inf, -math.inf):
        node = SimpleNamespace(odom_at=10., speed=0., angular=0., max_speed=.2)
        values = [0., 0., 0.]
        values[axis] = value
        with patch('land_clearance.mission_node.time.monotonic', return_value=11.):
            try:
                MissionNode.on_odom(node, message(*values))
            except RuntimeError as exc:
                assert 'Invalid odometry velocity' in str(exc)
            else:
                raise AssertionError(f'Invalid odometry accepted: axis={axis}, value={value}')
        assert leased_motion_mode('nav', 11.-node.odom_at) == 'stop'
        assert node.max_speed == .2, 'Invalid data polluted maximum-speed evidence'

node = SimpleNamespace(odom_at=10., speed=0., angular=0., max_speed=.2)
with patch('land_clearance.mission_node.time.monotonic', return_value=11.):
    MissionNode.on_odom(node, message(.3, .4, -.1))
assert (node.odom_at, node.speed, node.angular, node.max_speed) == (11., .5, .1, .5)
print('PASS: invalid odometry rejects and revokes movement lease; finite odometry preserved')
