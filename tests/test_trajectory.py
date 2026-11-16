import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from trajectory_geometry import segment_box_distance


class TrajectoryTests(unittest.TestCase):
    def test_segment_crosses_thin_target_between_noncontact_samples(self):
        distance, point = segment_box_distance((-1,0,0),(1,0,0),(.01,.09,.035))
        self.assertAlmostEqual(distance,0.)
        self.assertLessEqual(abs(point[0]),.01+1e-8)

    def test_near_miss_and_stationary_and_invalid(self):
        distance,_=segment_box_distance((-1,.12,0),(1,.12,0),(.01,.09,.035))
        self.assertAlmostEqual(distance,.03)
        distance,_=segment_box_distance((.03,0,0),(.03,0,0),(.01,.09,.035))
        self.assertAlmostEqual(distance,.02)
        with self.assertRaises(ValueError):
            segment_box_distance((float('nan'),0,0),(1,0,0),(.01,.09,.035))
