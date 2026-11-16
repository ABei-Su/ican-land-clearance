import unittest
from land_clearance.guards import StableLabel, VelocityGate


class GuardTests(unittest.TestCase):
    def test_invalid_active_command_clears_previous_motion_without_crashing(self):
        for axis in range(3):
            for value in (float('nan'), float('inf'), -float('inf')):
                with self.subTest(axis=axis, value=value):
                    g = VelocityGate()
                    g.heartbeat('nav', 1.)
                    g.receive('nav', (.2, 0., 0.), 1.01)
                    command = [0., 0., 0.]
                    command[axis] = value
                    g.receive('nav', command, 1.02)
                    self.assertEqual(g.output(1.03), (0., 0., 0.))
                    g.heartbeat('nav', 1.04)
                    self.assertEqual(g.output(1.05), (0., 0., 0.))
                    g.receive('nav', (.1, 0., 0.), 1.06)
                    self.assertEqual(g.output(1.07), (.1, 0., 0.))

    def test_invalid_inactive_source_cannot_replace_active_motion(self):
        g = VelocityGate()
        g.heartbeat('aim', 1.)
        g.receive('aim', (0., 0., .12), 1.01)
        g.receive('nav', (float('nan'), 0., 0.), 1.02)
        self.assertEqual(g.output(1.03), (0., 0., .12))

    def test_label_requires_distinct_consistent_frames(self):
        g = StableLabel(count=3)
        self.assertIsNone(g.update('rescue_camp', 1., 1.1))
        self.assertIsNone(g.update('rescue_camp', 1., 1.2))
        self.assertIsNone(g.update('rescue_camp', 1.2, 1.3))
        self.assertEqual(g.update('rescue_camp', 1.3, 1.4), 'rescue_camp')
        self.assertIsNone(g.update(None, 1.4, 1.5))

    def test_stale_and_changed_labels_reset(self):
        g = StableLabel(count=2)
        g.update('rescue_camp', 1., 1.)
        self.assertIsNone(g.update('landslide', 1.1, 1.1))
        self.assertIsNone(g.update('landslide', 1.2, 3.))
        self.assertIsNone(g.update('landslide', 3., 3.))

    def test_gate_mode_watchdog_and_switch(self):
        g = VelocityGate()
        g.receive('nav', (1., 1., 2.), 1.)
        self.assertEqual(g.output(1.1), (0., 0., 0.))
        g.select('nav')
        self.assertEqual(g.output(1.1), (0., 0., 0.))
        g.heartbeat('nav', 2.)
        g.receive('nav', (.2, 0., 0.), 2.)
        self.assertEqual(g.output(2.1), (.2, 0., 0.))
        self.assertEqual(g.output(2.5), (0., 0., 0.))
        g.select('aim')
        g.receive('nav', (.2, 0., 0.), 3.)
        self.assertEqual(g.output(3.), (0., 0., 0.))
        with self.assertRaises(ValueError):
            g.select('invalid')

    def test_controller_lease_expiry_stops_even_with_live_navigation(self):
        g = VelocityGate()
        g.heartbeat('nav', 1.)
        g.receive('nav', (.2, 0., 0.), 1.1)
        self.assertEqual(g.output(1.2), (.2, 0., 0.))
        g.receive('nav', (.2, 0., 0.), 2.)
        self.assertEqual(g.output(2.), (0., 0., 0.))
        g.heartbeat('nav', 2.1)
        self.assertEqual(g.output(2.1), (0., 0., 0.))
        g.receive('nav', (.2, 0., 0.), 2.2)
        self.assertEqual(g.output(2.25), (.2, 0., 0.))
