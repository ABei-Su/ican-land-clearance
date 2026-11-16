"""Read-camera/rotate-only diagnostic at the current fixed shooting point. No fire."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/land_clearance'))
import rclpy
from land_clearance.mission_node import MissionNode
rclpy.init()
n = MissionNode()
n.label = 'landslide'
try:
    n.wait(lambda: n.frame is not None and n.info is not None and n.odom_at > 0, 20)
    n.aim()
finally:
    n.stop()
    n.logfile.close()
    n.destroy_node()
    rclpy.shutdown()
