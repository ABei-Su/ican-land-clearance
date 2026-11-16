"""Pure score equivalence, independent of OpenCV and ROS installations."""
import unittest
import numpy as np
from land_clearance.marker_scores import MarkerScores


class MarkerScoreTests(unittest.TestCase):
    def test_matches_reference_for_noisy_rotated_and_ambiguous_codes(self):
        rng = np.random.default_rng(20261020)
        codes = {index: rng.integers(0, 2, (5, 5)).astype(bool) for index in range(1, 9)}
        # Include an exact competitor to exercise equal-score ordering.
        codes[8] = codes[7].copy()
        scorer = MarkerScores(codes)
        samples = [rng.integers(0, 2, (5, 5)).astype(bool) for _ in range(256)]
        for template in codes.values():
            for rotation in range(4):
                for bit in range(-1, 25):
                    code = np.rot90(template, rotation).copy()
                    if bit >= 0:
                        code.flat[bit] = not code.flat[bit]
                    samples.append(code)
        for code in samples:
            expected = sorted([
                (max(float(np.mean(np.rot90(code, k) == template)) for k in range(4)), marker_id)
                for marker_id, template in codes.items()
            ], reverse=True)
            self.assertEqual(scorer.scores(code), expected)

    def test_snapshots_templates_and_does_not_mutate_candidate(self):
        code = np.eye(5, dtype=bool)
        original = code.copy()
        scorer = MarkerScores({1: code})
        code[:] = False
        self.assertEqual(scorer.scores(original), [(1., 1)])
        np.testing.assert_array_equal(original, np.eye(5, dtype=bool))
