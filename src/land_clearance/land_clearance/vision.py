"""Public-template ground recognition with geometric verification."""
from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np
from .core import LABELS


def ground_view(bgr, *, fx, fy, cx, cy, height):
    """Rectify horizontal ground for the documented level forward camera.

    Height is measured above the target top, in metres. Caller supplies camera
    intrinsics. Output covers 0.15..0.95 m forward and +/-0.6 m laterally.
    This model is invalid for a pitched or rolled camera.
    """
    if not all(np.isfinite(v) for v in (fx, fy, cx, cy, height)) or min(fx, fy, height) <= 0:
        raise ValueError('Invalid camera geometry')
    x = np.broadcast_to(np.linspace(.95, .15, 800)[:, None], (800, 800))
    y = np.broadcast_to(np.linspace(.6, -.6, 800)[None, :], (800, 800))
    u = (cx - y * fx / x).astype(np.float32)
    v = (cy + height * fy / x).astype(np.float32)
    return cv2.remap(bgr, u, v, cv2.INTER_LINEAR)


@dataclass(frozen=True)
class Detection:
    label: str
    inliers: int
    confidence: float
    polygon: np.ndarray


class GroundMatcher:
    def __init__(self, directory: Path):
        self.sift = cv2.SIFT_create(nfeatures=1800, contrastThreshold=0.025)
        self.matcher = cv2.BFMatcher(cv2.NORM_L2)
        self.templates = []
        for path in sorted(Path(directory).iterdir()):
            label = path.stem.rsplit('_', 1)[0]
            if label not in LABELS:
                continue
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise ValueError(f'Unreadable template: {path.name}')
            scale = min(1., 800 / max(image.shape))
            original = cv2.resize(image, None, fx=scale, fy=scale)
            # Ground textures stretch source photos to the physical board.
            # Square-normalized variants remove source aspect ratio distortion.
            for variant in (original, cv2.resize(image, (400, 400))):
                keys, desc = self.sift.detectAndCompute(variant, None)
                if desc is None:
                    raise ValueError(f'No features: {path.name}')
                self.templates.append((label, variant.shape, keys, desc))
        if {t[0] for t in self.templates} != set(LABELS):
            raise ValueError('All five ground classes are required')

    def detect(self, bgr) -> Detection | None:
        if bgr is None or bgr.size == 0:
            return None
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        keys, desc = self.sift.detectAndCompute(gray, None)
        if desc is None or len(desc) < 8:
            return None
        candidates = {}
        for label, shape, template_keys, template_desc in self.templates:
            pairs = self.matcher.knnMatch(template_desc, desc, k=2)
            good = [a for pair in pairs if len(pair) == 2 for a, b in [pair] if a.distance < .72 * b.distance]
            if len(good) < 9:
                continue
            source = np.float32([template_keys[m.queryIdx].pt for m in good])
            target = np.float32([keys[m.trainIdx].pt for m in good])
            hom, mask = cv2.findHomography(source, target, cv2.RANSAC, 4.)
            if hom is None or mask is None or not np.isfinite(hom).all():
                continue
            count = int(mask.sum())
            if count < 9 or count / len(good) < .45:
                continue
            h, w = shape
            corners = np.float32([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]])
            polygon = cv2.perspectiveTransform(corners[None], hom)[0]
            area = abs(cv2.contourArea(polygon))
            if not np.isfinite(polygon).all() or not cv2.isContourConvex(polygon) or area < 250:
                continue
            height, width = gray.shape
            if area > height * width * 1.5 or np.any(polygon < -100) or np.any(polygon[:, 0] > width + 100) or np.any(polygon[:, 1] > height + 100):
                continue
            item = Detection(label, count, count / len(good), polygon)
            if label not in candidates or count > candidates[label].inliers:
                candidates[label] = item
        # Multiple geometrically valid classes require a narrower observation,
        # not guessing based on which texture happens to have more keypoints.
        return next(iter(candidates.values())) if len(candidates) == 1 else None
