import math
import unittest
from land_clearance.route import OBSERVATIONS, TARGETS, load_route


class RouteTests(unittest.TestCase):
    def test_four_observations_are_outside_target_footprints(self):
        self.assertEqual(len(OBSERVATIONS), 4)
        self.assertEqual(len(TARGETS), 4)
        for observation, target in zip(OBSERVATIONS, TARGETS):
            self.assertGreaterEqual(math.dist(observation[:2], target[:2]), .55)

    def test_rejects_incomplete_nonfinite_or_overlap_route(self):
        for observations in ([], [(math.nan, 0, 0)]*4, TARGETS):
            with self.assertRaises(ValueError):
                load_route(observations, TARGETS)
