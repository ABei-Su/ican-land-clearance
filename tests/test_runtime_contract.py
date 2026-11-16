import unittest
from land_clearance.runtime_contract import safe_to_fire, missing_runtime_inputs
from land_clearance.runtime_contract import exclusive_velocity_owner, leased_motion_mode


class RuntimeContractTests(unittest.TestCase):
    def test_startup_reports_exact_missing_input_including_stale_odometry(self):
        self.assertEqual(missing_runtime_inputs(1., True, False, True, True, .1), ['camera_image'])
        self.assertEqual(missing_runtime_inputs(1., True, True, True, True, .1), [])
        self.assertEqual(missing_runtime_inputs(0., False, False, False, False, float('inf')),
                         ['clock','camera_info','camera_image','navigation','shooter','odometry'])

    def test_camera_alignment_does_not_authorize_fire_after_odometry_loss(self):
        self.assertTrue(safe_to_fire(.02,0.,0.,.05,.04))
        for ages in [(.31,.05,.04),(.02,.26,.04),(.02,.05,.26)]:
            self.assertFalse(safe_to_fire(ages[0],0.,0.,ages[1],ages[2]))
        for value in [float('nan'),float('inf'),.1]:
            self.assertFalse(safe_to_fire(.02,value,0.,.05,.04))

    def test_requires_exactly_one_gate_writer(self):
        self.assertTrue(exclusive_velocity_owner(['land_velocity_gate']))
        for writers in ([], ['controller_server'], ['land_velocity_gate', 'controller_server'],
                        ['land_velocity_gate', 'land_velocity_gate']):
            self.assertFalse(exclusive_velocity_owner(writers))

    def test_stale_odometry_stops_before_failure_timeout(self):
        self.assertEqual(leased_motion_mode('nav', .1), 'nav')
        self.assertEqual(leased_motion_mode('aim', .1), 'aim')
        for age in (.31, 1., 2., float('nan'), -1.):
            self.assertEqual(leased_motion_mode('nav', age), 'stop')
        self.assertEqual(leased_motion_mode('stop', .1), 'stop')
