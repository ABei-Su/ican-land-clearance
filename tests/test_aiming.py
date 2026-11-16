from pathlib import Path
import unittest
import json
import cv2
import numpy as np
from land_clearance.aiming import ring_center, AimGuard, angular_command, vertical_aligned


class AimingTests(unittest.TestCase):
    def test_stalled_rotation_gets_bounded_recovery_but_alignment_still_stops(self):
        self.assertEqual(angular_command(-7., 476., stalled=True), .22)
        self.assertEqual(angular_command(7., 476., stalled=True), -.22)
        self.assertEqual(angular_command(2., 476., stalled=True), 0.)

    def test_moving_marker_height_result_can_be_logged_as_json(self):
        y = np.float64(400.5-(.26-.12839364)*476/.97)
        valid = vertical_aligned(y, 476., 400.5, 3, 7)
        self.assertEqual(json.loads(json.dumps({'valid':valid})), {'valid':True})
        self.assertFalse(vertical_aligned(y+10,476.,400.5,3,7))

    def test_small_visible_error_overcomes_observed_rotation_stall(self):
        self.assertEqual(angular_command(-5., 476.), .12)
        self.assertEqual(angular_command(5., 476.), -.12)
        self.assertEqual(angular_command(3., 476.), 0.)
        self.assertEqual(angular_command(500., 476.), -.15)
        for error, fx in [(float('nan'), 476.), (5., 0.), (5., float('inf'))]:
            with self.assertRaises(ValueError):
                angular_command(error, fx)

    def test_real_ring_center(self):
        image = cv2.imread(str(Path(__file__).parent / 'fixtures/ring-observation.png'))
        center = ring_center(image)
        self.assertIsNotNone(center)
        np.testing.assert_allclose(center, (405, 358), atol=5)

    def test_blank_and_single_color_not_ring(self):
        image = np.zeros((300, 300, 3), np.uint8)
        self.assertIsNone(ring_center(image))
        cv2.circle(image, (150, 150), 50, (0, 0, 255), -1)
        self.assertIsNone(ring_center(image))

    def test_fire_requires_fresh_distinct_aligned_frames_and_stationary_robot(self):
        guard = AimGuard()
        self.assertFalse(guard.update(2., 1., 1., .0))
        self.assertFalse(guard.update(2., 1., 1.1, .0))
        self.assertFalse(guard.update(2., 1.1, 1.1, .0))
        self.assertTrue(guard.update(2., 1.2, 1.2, .0))
        self.assertFalse(guard.update(2., 1.3, 1.3, .1))
        self.assertFalse(guard.update(2., 1.4, 2., .0))
        self.assertFalse(guard.update(None, 2., 2., .0))
        self.assertFalse(guard.update(20., 2.1, 2.1, .0))
