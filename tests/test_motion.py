import unittest

import numpy as np

from hornet_monitor.motion import MotionDetector


class MotionDetectorTests(unittest.TestCase):
    def test_detects_a_large_change_inside_roi(self):
        settings = {"roi": {"x": 10, "y": 10, "width": 80, "height": 80}, "min_area": 100, "threshold": 10, "blur_size": 5}
        detector = MotionDetector(settings)
        baseline = np.zeros((100, 100, 3), dtype=np.uint8)
        detector.detect(baseline)
        changed = baseline.copy()
        changed[30:60, 30:60] = 255
        self.assertTrue(detector.detect(changed).detected)

    def test_ignores_motion_outside_roi(self):
        settings = {"roi": {"x": 10, "y": 10, "width": 40, "height": 40}, "min_area": 100, "threshold": 10, "blur_size": 5}
        detector = MotionDetector(settings)
        baseline = np.zeros((100, 100, 3), dtype=np.uint8)
        detector.detect(baseline)
        changed = baseline.copy()
        changed[70:95, 70:95] = 255
        self.assertFalse(detector.detect(changed).detected)


if __name__ == "__main__":
    unittest.main()
