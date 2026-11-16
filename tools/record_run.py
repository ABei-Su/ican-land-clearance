"""Read-only local recording; simulator truth is saved separately, never controlled."""
import argparse
import json
import math
from pathlib import Path
import time
import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image
from std_msgs.msg import String
from gazebo_msgs.msg import ModelStates
from rclpy.qos import qos_profile_sensor_data

p = argparse.ArgumentParser()
p.add_argument('directory')
args = p.parse_args()
out = Path(args.directory)
out.mkdir(parents=True, exist_ok=False)
rclpy.init()
n = rclpy.create_node('local_evidence_recorder')
bridge = CvBridge()
state = {'phase': 'WAIT', 'point': 0}
frame = [None]
odom = [None]
ended = [None]
started = [False]
evidence = (out/'simulator-observations.jsonl').open('w', buffering=1)
events = (out/'events.jsonl').open('w', buffering=1)
timestamps = (out/'frame-times.jsonl').open('w', buffering=1)
frame_count = 0
writer = cv2.VideoWriter(str(out/'live.avi'), cv2.VideoWriter_fourcc(*'MJPG'), 10, (1200, 800))
if not writer.isOpened():
    raise RuntimeError('Video encoder unavailable')


def status(msg):
    item = json.loads(msg.data)
    state.update(item)
    started[0] = True
    events.write(msg.data+'\n')
    if item.get('event') == 'run_ended':
        ended[0] = time.monotonic()


def models(msg):
    if not started[0]:
        return
    selected = {}
    for name, pose, twist in zip(msg.name, msg.pose, msg.twist):
        if name.startswith('bullet_') or name.startswith('target_'):
            p, q = pose.position, pose.orientation
            selected[name] = [p.x, p.y, p.z, q.x, q.y, q.z, q.w]
    if any(name.startswith('bullet_') for name in selected):
        evidence.write(json.dumps({'wall_time': time.monotonic(), 'models': selected})+'\n')


n.create_subscription(Image, '/camera/image', lambda msg: frame.__setitem__(0, bridge.imgmsg_to_cv2(msg, 'bgr8')), qos_profile_sensor_data)
n.create_subscription(Odometry, '/odom', lambda msg: odom.__setitem__(0, msg), qos_profile_sensor_data)
n.create_subscription(String, '/mission/status', status, 100)
n.create_subscription(ModelStates, '/gazebo/model_states', models, qos_profile_sensor_data)
next_frame = time.monotonic()
deadline = next_frame+900
try:
    while time.monotonic() < deadline:
        rclpy.spin_once(n, timeout_sec=.01)
        now = time.monotonic()
        if ended[0] is not None and now-ended[0] > 1:
            break
        if now < next_frame or not started[0] or frame[0] is None:
            continue
        next_frame = now+.1
        canvas = np.full((800, 1200, 3), (25, 24, 22), np.uint8)
        canvas[:, :800] = cv2.resize(frame[0], (800, 800))
        lines = ['ICAN LAND CLEARANCE', 'Live camera + telemetry', '',
                 f'POINT {state.get("point", 0)} / 4', state.get('phase', ''),
                 state.get('event', ''), '', state.get('label', '')]
        if odom[0]:
            v = odom[0].twist.twist.linear
            lines.append(f'Speed: {math.hypot(v.x,v.y):.3f} m/s')
        lines += ['', 'LOCAL PRACTICE RUN', 'No official judge score']
        for index, line in enumerate(lines):
            cv2.putText(canvas, str(line), (820, 40+index*29), cv2.FONT_HERSHEY_SIMPLEX,
                        .58, (225, 225, 225), 1, cv2.LINE_AA)
        # Odom path location on a schematic of the public field, not a rendered camera.
        cv2.rectangle(canvas, (840, 465), (1150, 750), (120, 120, 120), 1)
        if odom[0]:
            pos = odom[0].pose.pose.position
            pixel = (int(850+(pos.x+.5)*100), int(475-pos.y*80))
            cv2.circle(canvas, pixel, 5, (60, 220, 240), -1)
        cv2.putText(canvas, 'ODOMETRY POSITION', (850, 785), cv2.FONT_HERSHEY_SIMPLEX, .5, (180,180,180), 1)
        writer.write(canvas)
        timestamps.write(json.dumps({'frame': frame_count, 'wall_time': now})+'\n')
        frame_count += 1
finally:
    writer.release()
    evidence.close()
    events.close()
    timestamps.close()
    (out/'recording.json').write_text(json.dumps({'fps':10, 'continuous_capture':True,
        'timing':'variable wall-clock samples; frame-times.jsonl required for final timing',
        'frames':frame_count, 'terminal':state}, indent=2))
    n.destroy_node()
    rclpy.shutdown()
