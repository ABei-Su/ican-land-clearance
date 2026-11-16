"""Sequential ROS adapter; the pure core owns all mission transitions."""
import json
import math
from pathlib import Path
import time
import uuid
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from lifecycle_msgs.srv import GetState
from sensor_msgs.msg import Image, CameraInfo, LaserScan
from std_msgs.msg import String
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformListener, TransformException
from .core import Mission, Phase, PHRASES, classify_target
from .guards import StableLabel
from .vision import GroundMatcher, ground_view
from .markers import MarkerDetector
from .aiming import AimGuard, ring_center, angular_command, vertical_aligned
from .precision import pose_command
from .route import load_route
from .runtime_contract import exclusive_velocity_owner, leased_motion_mode, safe_to_fire, missing_runtime_inputs


class StalePose(RuntimeError):
    pass


class MissionNode(Node):
    def __init__(self):
        super().__init__('land_mission')
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time', value=True)])
        self.declare_parameter('output_dir', str(Path.home() / 'land-runs'))
        self.declare_parameter('enable_shoot', False)
        self.declare_parameter('ready_timeout', 40.)
        self.core = Mission()
        self.observations, self.targets = load_route()
        self.run_id = uuid.uuid4().hex[:12]
        self.out = Path(self.get_parameter('output_dir').value) / self.run_id
        self.out.mkdir(parents=True)
        self.logfile = (self.out / 'events.jsonl').open('w', encoding='utf-8', buffering=1)
        share = Path(get_package_share_directory('land_clearance'))
        self.ground = GroundMatcher(share / 'assets/point_targets')
        self.markers = MarkerDetector(share / 'assets/markers')
        self.bridge = CvBridge()
        self.frame = None
        self.info = None
        self.scan = None
        self.odom_at = 0.
        self.aligned_at = self.aligned_stamp = -math.inf
        self.speed = self.angular = self.max_speed = 0.
        self.mode = 'stop'
        self.nav_goal = None
        self.shots = set()
        self.label = None
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.nav = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self.nav_state = self.create_client(GetState, '/bt_navigator/get_state')
        self.shooter = self.create_client(Trigger, '/shooter/shoot')
        self.mode_pub = self.create_publisher(String, '/mission/velocity_mode', 1)
        self.aim_pub = self.create_publisher(Twist, '/mission/aim_vel', 1)
        self.status_pub = self.create_publisher(String, '/mission/status', 10)
        self.referees = {name: self.create_publisher(String, '/referee/'+name, 10)
                         for name in ('detections', 'current_target', 'finish')}
        self.create_subscription(Image, '/camera/image', lambda msg: setattr(self, 'frame', msg), qos_profile_sensor_data)
        self.create_subscription(CameraInfo, '/camera/camera_info', lambda msg: setattr(self, 'info', msg), qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/scan', lambda msg: setattr(self, 'scan', msg), qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odom', self.on_odom, qos_profile_sensor_data)
        self.create_subscription(String, '/shooter/shot', lambda msg: self.shots.add(msg.data), 10)
        self.create_timer(.05, self.heartbeat)

    def on_odom(self, msg):
        speed = math.hypot(msg.twist.twist.linear.x, msg.twist.twist.linear.y)
        angular = abs(msg.twist.twist.angular.z)
        if not math.isfinite(speed) or not math.isfinite(angular):
            self.odom_at = -math.inf
            raise RuntimeError('Invalid odometry velocity')
        self.odom_at = time.monotonic()
        self.speed, self.angular = speed, angular
        self.max_speed = max(self.max_speed, self.speed)

    def heartbeat(self):
        mode = leased_motion_mode(self.mode, time.monotonic()-self.odom_at)
        self.mode_pub.publish(String(data=mode))

    def log(self, event, **data):
        item = {'version': 1, 'run': self.run_id, 'time': self.sim_now(),
                'point': self.core.point, 'phase': self.core.phase.name, 'event': event, **data}
        encoded = json.dumps(item, ensure_ascii=False)
        self.logfile.write(encoded+'\n')
        self.status_pub.publish(String(data=encoded))
        self.get_logger().info(encoded)

    def sim_now(self):
        return self.get_clock().now().nanoseconds*1e-9

    @staticmethod
    def stamp(msg):
        return msg.header.stamp.sec + msg.header.stamp.nanosec*1e-9

    def spin(self):
        rclpy.spin_once(self, timeout_sec=.025)
        if self.max_speed > .49:
            raise RuntimeError('Measured speed exceeded 0.49 m/s')
        if self.mode != 'stop' and time.monotonic()-self.odom_at > 2.:
            raise RuntimeError(f'Odometry lost during movement: mode={self.mode}, age={time.monotonic()-self.odom_at:.3f}s')

    def wait(self, predicate, timeout):
        end = time.monotonic()+timeout
        while not predicate():
            if time.monotonic() >= end:
                raise TimeoutError(f'Timeout in {self.core.phase.name}')
            self.spin()

    def future(self, future, timeout):
        self.wait(future.done, timeout)
        return future.result()

    def event(self, event):
        effects = self.core.apply(event, self.core.token)
        if not effects:
            raise RuntimeError(f'Illegal event {event}')
        self.log(event)

    def command(self, velocity):
        msg = Twist()
        msg.linear.x, msg.linear.y, msg.angular.z = velocity
        self.aim_pub.publish(msg)

    def stop(self):
        self.mode = 'stop'
        self.heartbeat()
        start = time.monotonic()
        self.wait(lambda: time.monotonic()-start > .4 and
                  time.monotonic()-self.odom_at < .3 and self.speed < .015 and self.angular < .02, 5)

    def map_pose(self):
        t = self.buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time())
        if abs(self.sim_now()-self.stamp(t)) > .4:
            raise StalePose('Stale map pose')
        p, q = t.transform.translation, t.transform.rotation
        return p.x, p.y, 2*math.atan2(q.z, q.w)

    def navigate(self, pose):
        self.mode = 'nav'
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x, goal.pose.pose.position.y = pose[:2]
        goal.pose.pose.orientation.z = math.sin(pose[2]/2)
        goal.pose.pose.orientation.w = math.cos(pose[2]/2)
        self.nav_goal = self.future(self.nav.send_goal_async(goal), 10)
        if not self.nav_goal.accepted:
            raise RuntimeError('Navigation rejected')
        result = self.future(self.nav_goal.get_result_async(), 75)
        self.nav_goal = None
        if result.status != 4:
            raise RuntimeError(f'Navigation failed: {result.status}')
        self.stop()
        self.log('final_approach_begin')
        self.mode = 'aim'
        end = time.monotonic()+30
        next_control = 0.
        diagnostics = {'stale_scan': 0, 'stale_pose': 0, 'commands': 0}
        last_pose = None
        next_diagnostic = 0.
        while time.monotonic() < end:
            self.spin()
            if time.monotonic() < next_control:
                continue
            next_control = time.monotonic()+.05
            if self.scan is None or not 0 <= self.sim_now()-self.stamp(self.scan) < .4:
                diagnostics['stale_scan'] += 1
                self.command((0., 0., 0.))
                continue
            ranges = [v for v in self.scan.ranges if math.isfinite(v) and self.scan.range_min <= v <= self.scan.range_max]
            if not ranges:
                raise RuntimeError('No valid laser clearance')
            try:
                current_pose = self.map_pose()
            except (TransformException, StalePose):
                diagnostics['stale_pose'] += 1
                self.command((0., 0., 0.))
                continue
            velocity, done = pose_command(current_pose, pose, min(ranges))
            diagnostics['commands'] += 1
            last_pose = current_pose
            self.command(velocity)
            if time.monotonic() >= next_diagnostic:
                self.log('final_approach_tracking', pose=current_pose, command=velocity,
                         measured_angular=self.angular, measured_speed=self.speed,
                         scan_age=self.sim_now()-self.stamp(self.scan),
                         odom_age=time.monotonic()-self.odom_at)
                next_diagnostic = time.monotonic()+2.
            if done:
                self.stop()
                self.log('arrived_precisely', pose=current_pose)
                return
        self.log('final_approach_timeout', diagnostics=diagnostics, last_pose=last_pose, goal=pose)
        raise TimeoutError('Final approach timeout')

    def fresh_frame(self, after, timeout=5):
        self.wait(lambda: self.frame is not None and self.stamp(self.frame) > after and
                  0 <= self.sim_now()-self.stamp(self.frame) < .2, timeout)
        msg = self.frame
        return self.bridge.imgmsg_to_cv2(msg, 'bgr8'), self.stamp(msg)

    def recognize(self):
        guard = StableLabel(max_age=1.5)
        after = self.sim_now()
        end = time.monotonic()+25
        while time.monotonic() < end:
            image, stamp = self.fresh_frame(after)
            after = stamp
            k = self.info.k
            ground = ground_view(image, fx=k[0], fy=k[4], cx=k[2], cy=k[5], height=.11639364)
            found = self.ground.detect(ground)
            label = guard.update(found.label if found else None, stamp, self.sim_now())
            if label:
                cv2.imwrite(str(self.out/f'point-{self.core.point}-recognition.png'), image)
                self.label = label
                self.log('recognized_image', label=label, inliers=found.inliers)
                return
        raise TimeoutError('No stable ground recognition')

    def aim(self):
        target = classify_target(self.label, self.core.point)
        guard = AimGuard()
        after = self.sim_now()
        previous = None
        next_diagnostic = 0.
        rotation_stall_at = time.monotonic()
        self.mode = 'aim'
        end = time.monotonic()+60
        while time.monotonic() < end:
            image, stamp = self.fresh_frame(after)
            after = stamp
            center = ring_center(image) if target == 0 else None
            if target:
                candidates = [m for m in self.markers.detect(image) if m.marker_id == target]
                if len(candidates) == 1:
                    center = candidates[0].center
            if center is None:
                self.command((0., 0., 0.))
                guard.update(None, stamp, self.sim_now(), self.speed)
                previous = None
                continue
            k = self.info.k
            x_error = float(center[0]-k[2])
            # Public board depth; category and marker position still come from camera.
            vertical_ok = vertical_aligned(center[1], k[4], k[5], self.core.point, target)
            if previous is not None and 0 < stamp-previous[1] <= .2:
                x_error += float(center[0]-previous[0])/(stamp-previous[1])*.06
            previous = (float(center[0]), stamp)
            now = time.monotonic()
            if abs(x_error) <= 3. or self.angular >= .01:
                rotation_stall_at = now
            stalled = now-rotation_stall_at > .8
            angular = angular_command(x_error, k[0], stalled=stalled)
            if stalled:
                rotation_stall_at = now
            self.command((0., 0., angular))
            if time.monotonic() >= next_diagnostic:
                self.log('aim_tracking', center=center.tolist(), error=x_error,
                         commanded_angular=angular, measured_angular=self.angular,
                         odom_age=time.monotonic()-self.odom_at,
                         frame_age=self.sim_now()-stamp, vertical_ok=vertical_ok)
                next_diagnostic = time.monotonic()+2.
            fresh_stationary = safe_to_fire(time.monotonic()-self.odom_at,
                self.speed, self.angular, 0., self.sim_now()-stamp)
            eligible = guard.update(x_error if vertical_ok and fresh_stationary else None,
                                    stamp, self.sim_now(), max(self.speed, self.angular))
            if eligible:
                self.command((0., 0., 0.))
                self.mode = 'stop'
                self.heartbeat()
                cv2.imwrite(str(self.out/f'point-{self.core.point}-aim.png'), image)
                self.log('aim_aligned', marker=target, center=center.tolist(), error=x_error)
                self.aligned_at, self.aligned_stamp = time.monotonic(), stamp
                return
        raise TimeoutError('No safe alignment window')

    def fire(self):
        if not self.get_parameter('enable_shoot').value:
            raise RuntimeError('Dry-run boundary reached before firing')
        if not safe_to_fire(time.monotonic()-self.odom_at, self.speed, self.angular,
                            time.monotonic()-self.aligned_at, self.sim_now()-self.aligned_stamp):
            raise RuntimeError('Firing rejected: stale alignment/odometry or robot moving')
        response = self.future(self.shooter.call_async(Trigger.Request()), 3)
        if not response.success:
            raise RuntimeError('Shooter rejected: '+response.message)
        name = response.message
        self.wait(lambda: name in self.shots, 3)
        self.log('bullet_spawn_observed', bullet=name, hit_confirmed=False)

    def run(self):
        try:
            def missing():
                return missing_runtime_inputs(self.sim_now(), self.info is not None, self.frame is not None,
                    self.nav.server_is_ready(), self.shooter.service_is_ready(), time.monotonic()-self.odom_at)
            try:
                self.wait(lambda: not missing(), float(self.get_parameter('ready_timeout').value))
            except TimeoutError as exc:
                raise TimeoutError('Runtime not ready: '+', '.join(missing())) from exc
            self.wait(lambda: bool(self.get_publishers_info_by_topic('/cmd_vel')), 15)
            self.wait(self.nav_state.service_is_ready, 30)
            activation_deadline = time.monotonic()+40
            while self.future(self.nav_state.call_async(GetState.Request()), 3).current_state.id != 3:
                if time.monotonic() >= activation_deadline:
                    raise TimeoutError('Navigation lifecycle did not become active')
                poll_at = time.monotonic()+.5
                self.wait(lambda: time.monotonic() >= poll_at, 1.)
            owners = [endpoint.node_name for endpoint in self.get_publishers_info_by_topic('/cmd_vel')]
            if not exclusive_velocity_owner(owners):
                raise RuntimeError(f'Unexpected velocity publishers: {owners}')
            self.event('ready')
            for point in range(4):
                self.navigate(self.observations[point])
                self.event('observed')
                self.recognize()
                self.event('recognized')
                self.referees['detections'].publish(String(data=PHRASES[self.label]))
                self.event('reported')
                self.navigate(self.targets[point])
                self.event('arrived')
                self.stop()
                self.event('stopped')
                self.referees['current_target'].publish(String(data=f'shoot_{point+1}'))
                self.event('declared')
                self.aim()
                self.event('aligned')
                self.fire()
                self.event('spawned')
                self.event('shot_recorded')
            self.navigate((0., 0., 0.))
            self.event('returned')
            self.stop()
            self.event('stopped')
            self.referees['finish'].publish(String(data='finish:return_start'))
            self.event('finished')
        except (Exception, KeyboardInterrupt) as exc:
            self.mode = 'stop'
            self.heartbeat()
            self.core.apply('failed', self.core.token)
            self.log('aborted', error=str(exc))
            if self.nav_goal is not None:
                try:
                    future = self.nav_goal.cancel_goal_async()
                    rclpy.spin_until_future_complete(self, future, timeout_sec=3)
                except Exception as cleanup_exc:
                    self.log('cleanup_error', stage='cancel', error=str(cleanup_exc))
        finally:
            self.mode = 'stop'
            for _ in range(5):
                self.heartbeat()
                try:
                    rclpy.spin_once(self, timeout_sec=.05)
                except Exception as cleanup_exc:
                    self.log('cleanup_error', stage='stop', error=str(cleanup_exc))
            try:
                self.log('run_ended', maximum_speed=self.max_speed, complete=self.core.phase == Phase.DONE)
            finally:
                self.logfile.close()
        return self.core.phase == Phase.DONE


def main():
    rclpy.init()
    node = MissionNode()
    success = node.run()
    node.destroy_node()
    rclpy.shutdown()
    raise SystemExit(0 if success else 1)
