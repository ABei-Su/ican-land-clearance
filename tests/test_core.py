import math
import unittest

from land_clearance.core import Mission, Phase, classify_target, limit_velocity


class CoreTests(unittest.TestCase):
    def test_mapping(self):
        labels = ['collapsed_ruins', 'landslide', 'trapped_people', 'damaged_vehicle', 'rescue_camp']
        for label, wheel, moving in zip(labels, range(1, 6), [6, 6, 7, 7, 8]):
            self.assertEqual(classify_target(label, 2), wheel)
            self.assertEqual(classify_target(label, 3), moving)
            self.assertEqual(classify_target(label, 4), moving)
            self.assertEqual(classify_target(label, 1), 0)
        with self.assertRaises(ValueError):
            classify_target('unknown', 2)

    def test_speed(self):
        for x, y in [(1, 1), (-1, -1), (0, 9), (0.1, -0.2)]:
            a, b, w = limit_velocity(x, y, 2)
            self.assertLessEqual(math.hypot(a, b), 0.40000001)
            self.assertLessEqual(abs(w), 0.6)
        for bad in [math.nan, math.inf, -math.inf]:
            self.assertEqual(limit_velocity(bad, 0, 0), (0., 0., 0.))

    def test_all_points_then_return(self):
        m = Mission()
        self.assertEqual(m.apply('ready', m.token), ['observe'])
        for point in range(1, 5):
            self.assertEqual(m.point, point)
            for event, effect in [('observed', 'recognize'), ('recognized', 'report'),
                                  ('reported', 'enter'), ('arrived', 'stop'),
                                  ('stopped', 'declare'), ('declared', 'aim'),
                                  ('aligned', 'fire'), ('spawned', 'record_shot')]:
                self.assertEqual(m.apply(event, m.token), [effect])
            self.assertEqual(m.apply('shot_recorded', m.token), ['observe' if point < 4 else 'return'])
        self.assertEqual(m.apply('returned', m.token), ['stop'])
        self.assertEqual(m.apply('stopped', m.token), ['finish'])
        self.assertEqual(m.apply('finished', m.token), ['stop'])
        self.assertEqual(m.phase, Phase.DONE)
        self.assertEqual(m.apply('ready', m.token), [])

    def test_invalid_stale_and_failure(self):
        m = Mission()
        old = m.token
        self.assertEqual(m.apply('aligned', old), [])
        m.apply('ready', old)
        self.assertEqual(m.apply('observed', old), [])
        self.assertEqual(m.apply('timeout', m.token), ['cancel', 'stop'])
        self.assertEqual(m.phase, Phase.ABORTED)
        self.assertEqual(m.apply('ready', m.token), [])

    def test_every_transient_failure(self):
        events = ['ready', 'observed', 'recognized', 'reported', 'arrived', 'stopped', 'declared', 'aligned']
        for prefix in range(len(events) + 1):
            for failure in ['timeout', 'failed', 'cancel', 'uncertain']:
                m = Mission()
                for event in events[:prefix]:
                    m.apply(event, m.token)
                self.assertEqual(m.apply(failure, m.token), ['cancel', 'stop'])
                self.assertEqual(m.phase, Phase.ABORTED)


if __name__ == '__main__':
    unittest.main()
