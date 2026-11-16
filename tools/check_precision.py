"""Local-only final-approach experiment; run only after Nav2 goal is cancelled."""
import argparse
import json
import math
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/land_clearance'))
import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from rclpy.qos import qos_profile_sensor_data
from tf2_ros import Buffer, TransformListener, TransformException
from land_clearance.precision import pose_command

p = argparse.ArgumentParser()
p.add_argument('--x', type=float, required=True)
p.add_argument('--y', type=float, required=True)
p.add_argument('--yaw', type=float, required=True)
args = p.parse_args()
goal = (args.x, args.y, args.yaw)
rclpy.init()
n = rclpy.create_node('precision_experiment')
n.set_parameters([rclpy.parameter.Parameter('use_sim_time', value=True)])
b = Buffer()
listener = TransformListener(b, n)
scan = [None, 0.]
speed = [0., 0.]
maximum = [0.]
pub = n.create_publisher(Twist, '/cmd_vel', 1)
report = {'goal': goal, 'status': 'failed'}


def odom(msg):
    v = msg.twist.twist.linear
    speed[:] = [math.hypot(v.x, v.y), time.monotonic()]
    maximum[0] = max(maximum[0], speed[0])


n.create_subscription(LaserScan, '/scan', lambda msg: scan.__setitem__(slice(None), [msg, time.monotonic()]), qos_profile_sensor_data)
n.create_subscription(Odometry, '/odom', odom, qos_profile_sensor_data)
try:
    end = time.monotonic() + 18
    while time.monotonic() < end:
        rclpy.spin_once(n, timeout_sec=.04)
        now = time.monotonic()
        if scan[0] is None or now-scan[1] > .4 or now-speed[1] > .4:
            pub.publish(Twist())
            continue
        if speed[0] > .12:
            raise RuntimeError('Final approach speed exceeded threshold')
        try:
            transform = b.lookup_transform('map', 'base_footprint', rclpy.time.Time())
        except TransformException:
            pub.publish(Twist())
            continue
        stamp = transform.header.stamp.sec + transform.header.stamp.nanosec*1e-9
        if abs(n.get_clock().now().nanoseconds*1e-9-stamp) > .4:
            pub.publish(Twist())
            continue
        t, q = transform.transform.translation, transform.transform.rotation
        pose = (t.x, t.y, 2*math.atan2(q.z, q.w))
        ranges = [r for r in scan[0].ranges if math.isfinite(r) and scan[0].range_min <= r <= scan[0].range_max]
        if not ranges:
            raise RuntimeError('No valid laser ranges')
        velocity, done = pose_command(pose, goal, min(ranges))
        report['last_map_pose'] = pose
        report['clearance'] = min(ranges)
        if done:
            report['status'] = 'position_reached'
            break
        msg = Twist()
        msg.linear.x, msg.linear.y, msg.angular.z = velocity
        pub.publish(msg)
    else:
        raise TimeoutError('Precision correction timeout')
except Exception as exc:
    report['error'] = str(exc)
finally:
    for _ in range(5):
        pub.publish(Twist())
        rclpy.spin_once(n, timeout_sec=.05)
    report['maximum_speed_mps'] = maximum[0]
    out = Path(__file__).resolve().parents[1] / f'reports/precision-{time.time_ns()}.json'
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    n.destroy_node()
    rclpy.shutdown()
raise SystemExit(0 if report['status'] == 'position_reached' else 1)
