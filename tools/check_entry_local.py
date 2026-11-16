"""Bounded entry diagnostic at point 2; uses the normal arbiter, no shots."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/land_clearance'))
import rclpy
from land_clearance.mission_node import MissionNode
rclpy.init()
n = MissionNode()
try:
    n.wait(lambda: n.nav.server_is_ready() and n.odom_at > 0, 20)
    n.navigate(n.targets[1])
finally:
    n.stop()
    n.logfile.close()
    n.destroy_node()
    rclpy.shutdown()
