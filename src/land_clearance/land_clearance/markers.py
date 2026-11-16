"""Camera-only matching of the competition's eight public marker textures."""
from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np
from .marker_scores import MarkerScores


def normalized(image):
    image = cv2.resize(image, (80, 80), interpolation=cv2.INTER_AREA)
    return cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def code_cells(image):
    """Sample the 5x5 code inside the two-cell border of a 9x9 marker."""
    return np.array([[np.mean(image[int((y+.35)*80/9):int((y+.65)*80/9)+1,
                                  int((x+.35)*80/9):int((x+.65)*80/9)+1]) > 127
                      for x in range(2, 7)] for y in range(2, 7)])


@dataclass(frozen=True)
class Marker:
    marker_id: int
    center: np.ndarray
    corners: np.ndarray
    confidence: float


class MarkerDetector:
    def __init__(self, directory):
        directory = Path(directory)
        self.templates = {}
        for marker_id in range(1, 6):
            image = cv2.imread(str(directory / f'{marker_id}.png'), 0)
            if image is None:
                raise ValueError(f'Missing marker {marker_id}')
            self.templates[marker_id] = normalized(image)
        board = cv2.imread(str(directory / 'board.png'), 0)
        if board is None:
            raise ValueError('Missing board texture')
        mask = cv2.threshold(board, 60, 255, cv2.THRESH_BINARY_INV)[1]
        mask[:5] = mask[-5:] = 0
        mask[:, :5] = mask[:, -5:] = 0
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = sorted(cv2.boundingRect(c) for c in contours)
        boxes = [(x, y, w, h) for x, y, w, h in boxes if w*h >= 10000 and .75 <= w/h <= 1.25]
        if len(boxes) != 3:
            raise ValueError('Expected three moving-board markers')
        for marker_id, (x, y, w, h) in zip((6, 7, 8), boxes):
            self.templates[marker_id] = normalized(board[y:y+h, x:x+w])
        self.codes = {marker_id: code_cells(template) for marker_id, template in self.templates.items()}
        self._score_table = MarkerScores(self.codes)

    def _scores(self, code):
        return self._score_table.scores(code)

    def detect(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Dark grey structural walls must not merge with black marker borders.
        mask = cv2.threshold(gray, 40, 255, cv2.THRESH_BINARY_INV)[1]
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []
        for contour in contours:
            if cv2.contourArea(contour) < 80:
                continue
            polygon = cv2.approxPolyDP(contour, .035*cv2.arcLength(contour, True), True)
            if len(polygon) != 4 or not cv2.isContourConvex(polygon):
                continue
            pts = polygon.reshape(4, 2).astype(np.float32)
            center = pts.mean(axis=0)
            pts = pts[np.argsort(np.arctan2(pts[:, 1]-center[1], pts[:, 0]-center[0]))]
            lengths = np.linalg.norm(pts - np.roll(pts, 1, axis=0), axis=1)
            if lengths.min() < 8 or lengths.max()/lengths.min() > 2:
                continue
            destination = np.float32([[0, 0], [79, 0], [79, 79], [0, 79]])
            tile = normalized(cv2.warpPerspective(gray, cv2.getPerspectiveTransform(pts, destination), (80, 80)))
            code = code_cells(tile)
            # Cell centres and thresholds are unchanged; compare all cached
            # template orientations in one array operation.
            scores = self._scores(code)
            score, marker_id = scores[0]
            # Reject weak matches and close competitors; never guess an ID.
            if score < .84 or score - scores[1][0] < .06:
                continue
            detections.append(Marker(marker_id, center, pts, score))
        return sorted(detections, key=lambda item: item.marker_id)
