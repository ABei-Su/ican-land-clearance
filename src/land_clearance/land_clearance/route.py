"""Public map geometry and experimentally checked pre-entry observation poses."""
import math

OBSERVATIONS = ((0., -.75, -math.pi/2), (0., -2.1, -math.pi/2),
                (.525, -1.925, 0.), (.525, -.775, 0.))
TARGETS = ((0., -1.35, 0.), (0., -2.70, 0.),
           (1.125, -1.925, -math.pi/2), (1.125, -.775, math.pi/2))


def load_route(observations=OBSERVATIONS, targets=TARGETS):
    if len(observations) != 4 or len(targets) != 4:
        raise ValueError('Exactly four ordered points required')
    for observation, target in zip(observations, targets):
        if len(observation) != 3 or len(target) != 3 or not all(math.isfinite(v) for v in (*observation, *target)):
            raise ValueError('Finite x/y/yaw triples required')
        if math.dist(observation[:2], target[:2]) < .55:
            raise ValueError('Observation overlaps entry clearance')
    return tuple(observations), tuple(targets)
