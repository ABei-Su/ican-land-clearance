"""Graph ownership contract; no ROS imports."""
import math


def missing_runtime_inputs(clock, info, image, navigation, shooter, odometry_age):
    ready = (math.isfinite(clock) and clock > 0, info, image, navigation, shooter,
             math.isfinite(odometry_age) and 0 <= odometry_age < .3)
    return [name for name, available in zip(
        ('clock','camera_info','camera_image','navigation','shooter','odometry'), ready)
        if not available]


def safe_to_fire(odometry_age, speed, angular, alignment_age, frame_age):
    values = (odometry_age, speed, angular, alignment_age, frame_age)
    return (all(math.isfinite(value) for value in values)
            and 0 <= odometry_age <= .3
            and abs(speed) <= .015 and abs(angular) <= .015
            and 0 <= alignment_age <= .25 and 0 <= frame_age <= .25)


def exclusive_velocity_owner(node_names):
    return list(node_names) == ['land_velocity_gate']


def leased_motion_mode(mode, odometry_age):
    if mode not in ('nav', 'aim') or not math.isfinite(odometry_age) or not 0 <= odometry_age <= .3:
        return 'stop'
    return mode
