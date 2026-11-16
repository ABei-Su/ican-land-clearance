"""Deterministic contracts; no ROS, clock, or simulator dependencies."""
from enum import Enum, auto
import math

LABELS = ('collapsed_ruins', 'landslide', 'trapped_people', 'damaged_vehicle', 'rescue_camp')
PHRASES = dict(zip(LABELS, (
    '已识别到坍塌废墟，前方道路被废墟阻断，开始清除障碍，打通救援通道。',
    '已识别到滑坡塌方，落石阻断救援道路，开始清除障碍，打通救援通道。',
    '已识别到被困人员，救援通道存在障碍，开始清除障碍，实施被困人员救援。',
    '已识别到受损车辆，车辆阻碍救援通道，开始清除障碍，实施被困人员救援。',
    '已识别到救援营地，前方存在障碍，开始清除障碍，建立救援通道。',
)))


def classify_target(label: str, point: int) -> int:
    if label not in LABELS or point not in (1, 2, 3, 4):
        raise ValueError('Unknown class or point')
    index = LABELS.index(label)
    return 0 if point == 1 else index + 1 if point == 2 else (6, 6, 7, 7, 8)[index]


def limit_velocity(x: float, y: float, w: float, limit: float = 0.4):
    if not all(math.isfinite(v) for v in (x, y, w, limit)) or limit <= 0:
        return (0., 0., 0.)
    scale = min(1., limit / max(math.hypot(x, y), 1e-12))
    return (x * scale, y * scale, max(-0.6, min(0.6, w)))


class Phase(Enum):
    INIT = auto()
    OBSERVE = auto()
    RECOGNIZE = auto()
    REPORT = auto()
    ENTER = auto()
    STOP = auto()
    DECLARE = auto()
    AIM = auto()
    FIRE = auto()
    SHOT = auto()
    RETURN = auto()
    RETURN_STOP = auto()
    FINISH = auto()
    DONE = auto()
    ABORTED = auto()


TRANSITIONS = {
    (Phase.INIT, 'ready'): (Phase.OBSERVE, 'observe'),
    (Phase.OBSERVE, 'observed'): (Phase.RECOGNIZE, 'recognize'),
    (Phase.RECOGNIZE, 'recognized'): (Phase.REPORT, 'report'),
    (Phase.REPORT, 'reported'): (Phase.ENTER, 'enter'),
    (Phase.ENTER, 'arrived'): (Phase.STOP, 'stop'),
    (Phase.STOP, 'stopped'): (Phase.DECLARE, 'declare'),
    (Phase.DECLARE, 'declared'): (Phase.AIM, 'aim'),
    (Phase.AIM, 'aligned'): (Phase.FIRE, 'fire'),
    (Phase.FIRE, 'spawned'): (Phase.SHOT, 'record_shot'),
    (Phase.RETURN, 'returned'): (Phase.RETURN_STOP, 'stop'),
    (Phase.RETURN_STOP, 'stopped'): (Phase.FINISH, 'finish'),
    (Phase.FINISH, 'finished'): (Phase.DONE, 'stop'),
}


class Mission:
    """Single writer. Callbacks must carry the generation token they started with."""

    def __init__(self):
        self._phase = Phase.INIT
        self._point = 1
        self._token = 0

    @property
    def phase(self):
        return self._phase

    @property
    def point(self):
        return self._point

    @property
    def token(self):
        return self._token

    def apply(self, event: str, token: int) -> list[str]:
        if token != self.token or self.phase in (Phase.DONE, Phase.ABORTED):
            return []
        if event in ('timeout', 'failed', 'cancel', 'uncertain'):
            self._phase = Phase.ABORTED
            effects = ['cancel', 'stop']
        elif self.phase == Phase.SHOT and event == 'shot_recorded':
            if self.point == 4:
                self._phase, effects = Phase.RETURN, ['return']
            else:
                self._point += 1
                self._phase, effects = Phase.OBSERVE, ['observe']
        elif (self.phase, event) in TRANSITIONS:
            self._phase, effect = TRANSITIONS[(self.phase, event)]
            effects = [effect]
        else:
            return []
        self._token += 1
        return effects
