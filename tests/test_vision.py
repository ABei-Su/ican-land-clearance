from pathlib import Path
import unittest
import cv2
import numpy as np
from land_clearance.vision import GroundMatcher, ground_view

ASSETS = Path(__file__).resolve().parents[1] / 'src/land_clearance/assets/point_targets'


class VisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setRNGSeed(123)
        cls.matcher = GroundMatcher(ASSETS)

    def test_blank_unknown(self):
        self.assertIsNone(self.matcher.detect(np.zeros((800, 800, 3), np.uint8)))

    def test_real_ground_observation(self):
        frame = cv2.imread(str(Path(__file__).parent / 'fixtures/ground-observation-1.png'))
        ground = ground_view(frame, fx=476.7, fy=476.7, cx=400, cy=400, height=.1164)
        result = self.matcher.detect(ground)
        self.assertIsNotNone(result)
        self.assertEqual(result.label, 'landslide')
        self.assertGreaterEqual(result.inliers, 15)

    def test_all_images_perspective(self):
        for path in sorted(ASSETS.iterdir()):
            with self.subTest(image=path.name):
                image = cv2.imread(str(path))
                h, w = image.shape[:2]
                hom = cv2.getPerspectiveTransform(
                    np.float32([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]]),
                    np.float32([[220, 310], [580, 310], [720, 700], [80, 700]]))
                frame = cv2.warpPerspective(image, hom, (800, 800))
                detection = self.matcher.detect(frame)
                self.assertIsNotNone(detection)
                self.assertEqual(detection.label, path.stem.rsplit('_', 1)[0])

    def test_two_equally_visible_classes_rejected(self):
        a = cv2.imread(str(next(ASSETS.glob('collapsed_ruins*'))))
        b = cv2.imread(str(next(ASSETS.glob('rescue_camp*'))))
        frame = np.concatenate([cv2.resize(a, (400, 400)), cv2.resize(b, (400, 400))], axis=1)
        self.assertIsNone(self.matcher.detect(frame))


if __name__ == '__main__':
    unittest.main()
