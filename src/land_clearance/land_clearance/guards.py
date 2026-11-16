"""Time-explicit perception and command guards, independently testable."""
import math
from .core import LABELS, limit_velocity


class StableLabel:
    def __init__(self, count=3, max_age=0.75):
        self.required, self.max_age = count, max_age
        self.label, self.count, self.last_stamp = None, 0, -math.inf

    def update(self, label, stamp, now):
        if label not in LABELS or not all(math.isfinite(t) for t in (stamp, now)) or not 0 <= now - stamp <= self.max_age:
            self.label, self.count = None, 0
            return None
        if stamp <= self.last_stamp:
            return None
        if stamp - self.last_stamp > self.max_age or label != self.label:
            self.count = 0
        self.last_stamp, self.label = stamp, label
        self.count += 1
        return label if self.count >= self.required else None


class VelocityGate:
    def __init__(self, timeout=0.3):
        self.mode = 'stop'
        self.timeout = timeout
        self.command, self.received = (0., 0., 0.), -math.inf
        self.lease = -math.inf

    def heartbeat(self, mode, now):
        if not math.isfinite(now) or now < self.lease:
            return
        if now - self.lease > .5:
            self.command, self.received = (0., 0., 0.), -math.inf
        self.select(mode)
        self.lease = now

    def select(self, mode):
        if mode not in ('nav', 'aim', 'stop'):
            raise ValueError('Unknown velocity source')
        if mode != self.mode:
            self.command, self.received = (0., 0., 0.), -math.inf
        self.mode = mode

    def receive(self, source, command, now):
        if source == self.mode and source in ('nav', 'aim') and math.isfinite(now):
            self.command, self.received = limit_velocity(*command), now

    def output(self, now):
        if self.mode == 'stop' or not math.isfinite(now) or not 0 <= now - self.received <= self.timeout or not 0 <= now - self.lease <= .5:
            return (0., 0., 0.)
        return self.command
