import math
import unittest
from land_clearance.precision import pose_command


class PrecisionTests(unittest.TestCase):
    def test_final_rotation_keeps_effective_command_until_inside_tolerance(self):
        velocity, done = pose_command((0., 0., 0.), (0., 0., .035), 1.)
        self.assertFalse(done)
        self.assertEqual(velocity, (0., 0., .12))
        velocity, done = pose_command((0., 0., 0.), (.05, 0., .02), 1.)
        self.assertFalse(done)
        self.assertEqual(velocity[2], 0.)

    def test_world_error_rotates_into_robot_frame(self):
        velocity, done = pose_command((0, 0, math.pi/2), (.1, 0, math.pi/2), 1.)
        self.assertFalse(done)
        self.assertAlmostEqual(velocity[0], 0.)
        self.assertLess(velocity[1], 0.)
        self.assertLessEqual(math.hypot(*velocity[:2]), .08)

    def test_obstacle_or_large_error_or_invalid_data_rejects(self):
        for current, goal, clearance in [((0,0,0),(.1,0,0),.1),
                                         ((0,0,0),(1,0,0),1.),
                                         ((math.nan,0,0),(0,0,0),1.)]:
            with self.assertRaises(ValueError):
                pose_command(current, goal, clearance)

    def test_goal_requires_position_and_yaw_and_wraps_angle(self):
        self.assertEqual(pose_command((.005,0,0),(0,0,0),1.), ((0.,0.,0.), True))
        v, done = pose_command((0,0,math.pi-.02),(0,0,-math.pi+.02),1.)
        self.assertFalse(done)
        self.assertGreater(v[2], 0.)
        self.assertLessEqual(v[2], .2)
