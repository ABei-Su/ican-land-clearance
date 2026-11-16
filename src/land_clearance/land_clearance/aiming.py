"""Image geometry and time-explicit guards for conservative firing."""
import math
import cv2
import numpy as np


def vertical_aligned(center_y, fy, cy, point, target):
    depth = 1.49 if point <= 2 else .97
    expected = cy-(.26-.12839364)*fy/depth
    return bool(target == 0 or abs(center_y-expected) <= 6)


def angular_command(error, fx, stalled=False):
    if not math.isfinite(error) or not math.isfinite(fx) or fx <= 0:
        raise ValueError('Invalid image error or focal length')
    if abs(error) <= 3.:
        return 0.
    if stalled:
        return -math.copysign(.22, error)
    # Cold-start trials showed 0.01 and 0.04 rad/s can stall despite delivery.
    return -math.copysign(min(.15, max(.12, .9*abs(error)/fx)), error)


def ring_center(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, (0, 70, 45), (15, 255, 255)) | cv2.inRange(hsv, (165, 70, 45), (179, 255, 255))
    blue = cv2.inRange(hsv, (85, 50, 35), (130, 255, 255))
    groups = []
    for mask in (red, blue):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            x, y, w, h = cv2.boundingRect(contour)
            if area < 60 or perimeter <= 0 or not .7 < w/h < 1.4:
                continue
            if 4*math.pi*area/(perimeter*perimeter) < .5:
                continue
            moments = cv2.moments(contour)
            candidates.append((np.array([moments['m10']/area, moments['m01']/area]), area))
        groups.append(candidates)
    matches = []
    for r, ra in groups[0]:
        for b, ba in groups[1]:
            if ra > ba and np.linalg.norm(r-b) < max(3., .12*math.sqrt(ra)):
                matches.append((r+b)/2)
    return matches[0] if len(matches) == 1 else None


class AimGuard:
    def __init__(self, tolerance_px=3., frames=3):
        self.tolerance = tolerance_px
        self.frames = frames
        self.count = 0
        self.last_stamp = -math.inf

    def update(self, error, stamp, now, speed):
        if error is None or not all(math.isfinite(v) for v in (error, stamp, now, speed)) or not 0 <= now-stamp <= .25 or abs(error) > self.tolerance or abs(speed) > .015:
            self.count = 0
            return False
        if stamp <= self.last_stamp:
            return False
        if stamp-self.last_stamp > .25:
            self.count = 0
        self.last_stamp = stamp
        self.count += 1
        return self.count >= self.frames
