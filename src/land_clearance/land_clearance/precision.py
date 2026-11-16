"""Bounded final-approach controller; caller must verify fresh TF and laser."""
import math
from .core import limit_velocity


def pose_command(current, goal, clearance):
    if not all(math.isfinite(v) for v in (*current, *goal, clearance)):
        raise ValueError('Invalid pose or clearance')
    if clearance < .20:
        raise ValueError('Obstacle clearance below final-approach margin')
    dx, dy = goal[0]-current[0], goal[1]-current[1]
    distance = math.hypot(dx, dy)
    if distance > .20:
        raise ValueError('Outside final-approach envelope')
    yaw = current[2]
    error = math.atan2(math.sin(goal[2]-yaw), math.cos(goal[2]-yaw))
    if distance <= .02 and abs(error) <= .03:
        return (0., 0., 0.), True
    x = .8*(math.cos(yaw)*dx + math.sin(yaw)*dy)
    y = .8*(-math.sin(yaw)*dx + math.cos(yaw)*dy)
    if distance <= .02:
        x = y = 0.
    w = 0. if abs(error) <= .03 else math.copysign(min(.2, max(.12, abs(error))), error)
    return limit_velocity(x, y, w, limit=.08), False
