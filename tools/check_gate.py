"""ROS transport contract test. Run in isolated ROS_DOMAIN_ID=71, not a live robot."""
import math
import os
import signal
import subprocess
import time
import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import String

if os.environ.get('ROS_DOMAIN_ID') != '71':
    raise SystemExit('Run with ROS_DOMAIN_ID=71 to isolate the test from simulation')

rclpy.init()
node = rclpy.create_node('gate_contract_test')
mode = node.create_publisher(String, '/mission/velocity_mode', 1)
nav = node.create_publisher(Twist, '/mission/nav_vel', 1)
samples = []
node.create_subscription(Twist, '/cmd_vel', lambda msg: samples.append(
    (time.monotonic(), msg.linear.x, msg.linear.y, msg.angular.z)), 10)
process = subprocess.Popen(['ros2', 'run', 'land_clearance', 'velocity_gate'], start_new_session=True)


def drive(seconds, heartbeat):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if heartbeat:
            msg = String()
            msg.data = 'nav'
            mode.publish(msg)
        command = Twist()
        command.linear.x = command.linear.y = 1.
        nav.publish(command)
        rclpy.spin_once(node, timeout_sec=.05)
        time.sleep(.03)


try:
    deadline = time.monotonic() + 20.
    while (mode.get_subscription_count() == 0 or nav.get_subscription_count() == 0) and time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Gate exited during startup: {process.returncode}')
        rclpy.spin_once(node, timeout_sec=.1)
    assert mode.get_subscription_count() and nav.get_subscription_count(), 'Gate discovery timeout'
    drive(4., True)
    assert samples, 'No velocity output'
    assert any(math.hypot(x, y) > .39 for _, x, y, _ in samples), 'No forwarded command'
    assert all(math.hypot(x, y) <= .400001 for _, x, y, _ in samples), 'Vector speed exceeded cap'
    stopped_after = time.monotonic() + .8
    drive(2., False)
    after = [s for s in samples if s[0] > stopped_after]
    assert after and all(x == y == w == 0. for _, x, y, w in after), 'Lease expiry failed to stop'
    print('PASS: ROS command routing, diagonal cap, and control-heartbeat loss stop')
finally:
    os.killpg(process.pid, signal.SIGINT)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    node.destroy_node()
    rclpy.shutdown()
