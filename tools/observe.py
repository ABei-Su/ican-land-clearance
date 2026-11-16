"""Bounded local navigation experiment; never publishes referee or shot events."""
import argparse
import json
import math
from pathlib import Path
import time
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/land_clearance'))
import cv2
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo
from land_clearance.vision import GroundMatcher, ground_view

p = argparse.ArgumentParser()
p.add_argument('--x', type=float, required=True)
p.add_argument('--y', type=float, required=True)
p.add_argument('--yaw', type=float, required=True)
p.add_argument('--name', required=True)
args = p.parse_args()
root = Path(__file__).resolve().parents[1]
out = root / 'reports' / args.name
out.mkdir(parents=True, exist_ok=True)
rclpy.init()
n = rclpy.create_node('observation_experiment')
n.set_parameters([rclpy.parameter.Parameter('use_sim_time', value=True)])
bridge = CvBridge()
matcher = GroundMatcher(root / 'src/land_clearance/assets/point_targets')
latest = [None, 0.]
intrinsics = [None]
max_speed = [0.]


def camera(msg):
    latest[:] = [msg, time.monotonic()]


def odom(msg):
    v = msg.twist.twist.linear
    max_speed[0] = max(max_speed[0], math.hypot(v.x, v.y))
    p = msg.pose.pose
    report['last_odometry'] = {'x': p.position.x, 'y': p.position.y,
                              'yaw': 2*math.atan2(p.orientation.z, p.orientation.w)}


n.create_subscription(Image, '/camera/image', camera, qos_profile_sensor_data)
n.create_subscription(CameraInfo, '/camera/camera_info', lambda msg: intrinsics.__setitem__(0, msg), qos_profile_sensor_data)
n.create_subscription(Odometry, '/odom', odom, qos_profile_sensor_data)
stop = n.create_publisher(Twist, '/cmd_vel', 10)
client = ActionClient(n, NavigateToPose, '/navigate_to_pose')
handle = None
report = {'goal': vars(args), 'status': 'failed'}


def feedback(message):
    f = message.feedback
    p = f.current_pose.pose
    report['last_navigation_feedback'] = {'distance_remaining': f.distance_remaining,
        'x': p.position.x, 'y': p.position.y,
        'yaw': 2*math.atan2(p.orientation.z, p.orientation.w)}


def wait(future, seconds):
    end = time.monotonic() + seconds
    while not future.done() and time.monotonic() < end:
        rclpy.spin_once(n, timeout_sec=.1)
        if max_speed[0] > .49:
            raise RuntimeError('Measured speed exceeded experiment threshold')
    if not future.done():
        raise TimeoutError('Experiment timeout')
    return future.result()


try:
    if not client.wait_for_server(timeout_sec=15):
        raise RuntimeError('Nav2 unavailable')
    goal = NavigateToPose.Goal()
    goal.pose.header.frame_id = 'map'
    goal.pose.header.stamp = n.get_clock().now().to_msg()
    goal.pose.pose.position.x, goal.pose.pose.position.y = args.x, args.y
    goal.pose.pose.orientation.z = math.sin(args.yaw / 2)
    goal.pose.pose.orientation.w = math.cos(args.yaw / 2)
    handle = wait(client.send_goal_async(goal, feedback_callback=feedback), 15)
    if not handle.accepted:
        raise RuntimeError('Goal rejected')
    result = wait(handle.get_result_async(), 90)
    report['nav_status'] = result.status
    if result.status != 4:
        raise RuntimeError(f'Navigation failed: {result.status}')
    received_after = time.monotonic()
    deadline = received_after + 15
    while latest[1] <= received_after and time.monotonic() < deadline:
        rclpy.spin_once(n, timeout_sec=.1)
    if latest[1] <= received_after:
        raise RuntimeError('No fresh camera frame after arrival')
    image = bridge.imgmsg_to_cv2(latest[0], 'bgr8')
    info = intrinsics[0]
    if info is None:
        raise RuntimeError('No camera calibration')
    ground = ground_view(image, fx=info.k[0], fy=info.k[4], cx=info.k[2], cy=info.k[5], height=.11639364)
    detection = matcher.detect(ground)
    cv2.imwrite(str(out / 'camera.png'), image)
    cv2.imwrite(str(out / 'ground.png'), ground)
    report['recognition'] = None if detection is None else {
        'label': detection.label, 'inliers': detection.inliers,
        'confidence': detection.confidence, 'polygon': detection.polygon.tolist()}
    report['status'] = 'observed'
except Exception as exc:
    report['error'] = str(exc)
    if latest[0] is not None:
        cv2.imwrite(str(out / 'failure-camera.png'), bridge.imgmsg_to_cv2(latest[0], 'bgr8'))
finally:
    if handle is not None:
        cancel = handle.cancel_goal_async()
        rclpy.spin_until_future_complete(n, cancel, timeout_sec=3)
    for _ in range(5):
        stop.publish(Twist())
        rclpy.spin_once(n, timeout_sec=.05)
    report['max_measured_speed_mps'] = max_speed[0]
    (out / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)
    n.destroy_node()
    rclpy.shutdown()
raise SystemExit(0 if report['status'] == 'observed' else 1)
