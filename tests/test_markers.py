from pathlib import Path
import unittest
import cv2
import numpy as np
from land_clearance.markers import MarkerDetector

ASSETS = Path(__file__).resolve().parents[1] / 'src/land_clearance/assets/markers'


class MarkerTests(unittest.TestCase):
    def setUp(self):
        self.detector = MarkerDetector(ASSETS)

    def test_batched_scores_preserve_rotations_noise_and_ambiguous_rankings(self):
        rng = np.random.default_rng(20261020)
        samples = [rng.integers(0, 2, (5, 5)).astype(bool) for _ in range(256)]
        for template in self.detector.codes.values():
            for rotation in range(4):
                code = np.rot90(template, rotation).copy()
                samples.append(code)
                for bit in range(25):
                    noisy = code.copy()
                    noisy.flat[bit] = not noisy.flat[bit]
                    samples.append(noisy)
        for code in samples:
            expected = sorted([
                (max(float(np.mean(np.rot90(code, k) == template)) for k in range(4)), marker_id)
                for marker_id, template in self.detector.codes.items()
            ], reverse=True)
            self.assertEqual(self.detector._scores(code), expected)

    def test_all_eight_ids_at_rotations(self):
        self.assertEqual(set(self.detector.templates), set(range(1, 9)))
        for marker_id, template in self.detector.templates.items():
            for rotation in range(4):
                with self.subTest(marker=marker_id, rotation=rotation):
                    frame = np.full((240, 320, 3), 255, np.uint8)
                    tile = cv2.resize(np.rot90(template, rotation).copy(), (44, 44))
                    frame[80:124, 120:164] = cv2.cvtColor(tile, cv2.COLOR_GRAY2BGR)
                    matches = self.detector.detect(frame)
                    self.assertEqual([m.marker_id for m in matches], [marker_id])
                    np.testing.assert_allclose(matches[0].center, [141.5, 101.5], atol=2)

    def test_unknown_solid_square_and_blank_rejected(self):
        frame = np.full((240, 320, 3), 255, np.uint8)
        self.assertEqual(self.detector.detect(frame), [])
        frame[80:130, 120:170] = 0
        self.assertEqual(self.detector.detect(frame), [])

    def test_two_distinct_markers(self):
        frame = np.full((240, 320, 3), 255, np.uint8)
        for marker_id, x in [(2, 40), (7, 190)]:
            tile = cv2.resize(self.detector.templates[marker_id], (50, 50))
            frame[80:130, x:x+50] = cv2.cvtColor(tile, cv2.COLOR_GRAY2BGR)
        self.assertEqual({m.marker_id for m in self.detector.detect(frame)}, {2, 7})

    def test_real_wheel_on_dark_wall(self):
        image = cv2.imread(str(Path(__file__).parent / 'fixtures/wheel-observation.png'))
        detections = self.detector.detect(image)
        wheel = [m for m in detections if 330 < m.center[0] < 440 and 310 < m.center[1] < 400]
        self.assertEqual({m.marker_id for m in wheel}, set(range(1, 6)))
