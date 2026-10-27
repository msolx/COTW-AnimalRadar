import unittest
from services.calibration import summarize,compare


class CalibrationTests(unittest.TestCase):
    def test_static_window(self):
        summary = summarize([(1,2,3),(1,2,3),(1,2,3)])
        self.assertEqual(summary['median_xyz'],(1,2,3))
        self.assertEqual(summary['max_spread_3d_m'],0)
        with self.assertRaises(ValueError):
            summarize([(float('nan'),0,0)])

    def test_delta_does_not_assert_compass_calibration(self):
        result = compare((10,20,30),(13,120,34))
        self.assertEqual(result['delta_xyz'],(3,100,4))
        self.assertEqual(result['horizontal_xz_m'],5)
        self.assertEqual(result['vertical_y_m'],100)
        self.assertFalse(result['axes_calibrated'])
