"""Only command-output owner. Navigation must be remapped to /mission/nav_vel."""
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from .guards import VelocityGate


class GateNode(Node):
    def __init__(self):
        super().__init__('land_velocity_gate')
        self.gate = VelocityGate()
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        for source in ('nav', 'aim'):
            self.create_subscription(Twist, f'/mission/{source}_vel',
                                     lambda msg, src=source: self.receive(src, msg), 1)
        self.create_subscription(String, '/mission/velocity_mode', self.mode, 1)
        # This node intentionally uses a steady wall clock, even if Gazebo pauses.
        self.create_timer(.05, self.publish)

    def mode(self, msg):
        if msg.data not in ('stop', 'nav', 'aim'):
            self.gate.select('stop')
            self.get_logger().error('Rejected invalid velocity mode')
            return
        self.gate.heartbeat(msg.data, time.monotonic())

    def receive(self, source, msg):
        self.gate.receive(source, (msg.linear.x, msg.linear.y, msg.angular.z), time.monotonic())

    def publish(self):
        x, y, w = self.gate.output(time.monotonic())
        msg = Twist()
        msg.linear.x, msg.linear.y, msg.angular.z = x, y, w
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = GateNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.gate.select('stop')
            node.publish()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
