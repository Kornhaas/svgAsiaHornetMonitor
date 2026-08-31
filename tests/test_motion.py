import unittest

import numpy as np

from hornet_monitor.motion import MotionDetector


class MotionDetectorTests(unittest.TestCase):
    def test_detects_a_large_change_inside_roi(self):
        settings = {
            "roi": {"x": 10, "y": 10, "width": 80, "height": 80},
            "min_area": 100,
            "threshold": 10,
            "blur_size": 5,
        }
        detector = MotionDetector(settings)
        baseline = np.zeros((100, 100, 3), dtype=np.uint8)
        detector.detect(baseline)
        changed = baseline.copy()
        changed[30:60, 30:60] = 255
        self.assertTrue(detector.detect(changed).detected)

    def test_ignores_motion_outside_roi(self):
        settings = {
            "roi": {"x": 10, "y": 10, "width": 40, "height": 40},
            "min_area": 100,
            "threshold": 10,
            "blur_size": 5,
        }
        detector = MotionDetector(settings)
        baseline = np.zeros((100, 100, 3), dtype=np.uint8)
        detector.detect(baseline)
        changed = baseline.copy()
        changed[70:95, 70:95] = 255
        self.assertFalse(detector.detect(changed).detected)

    def test_roi_update_resets_detector_and_rejects_out_of_bounds_roi(self):
        settings = {
            "roi": {"x": 0, "y": 0, "width": 50, "height": 50},
            "min_area": 100,
            "threshold": 10,
            "blur_size": 5,
        }
        detector = MotionDetector(settings)
        detector.update_roi({"x": 20, "y": 20, "width": 60, "height": 60}, 100, 100)
        self.assertEqual(detector.roi(), {"x": 20, "y": 20, "width": 60, "height": 60})
        with self.assertRaises(ValueError):
            detector.update_roi({"x": 90, "y": 0, "width": 20, "height": 20}, 100, 100)

    def test_detects_only_inside_inner_trigger_roi(self):
        settings = {
            "roi": {"x": 0, "y": 0, "width": 100, "height": 100},
            "min_area": 50,
            "threshold": 10,
            "blur_size": 5,
        }
        detector = MotionDetector(settings)
        detector.update_trigger_roi({"x": 30, "y": 30, "width": 40, "height": 40}, 100, 100)
        baseline = np.zeros((100, 100, 3), dtype=np.uint8)
        detector.detect(baseline)
        outside = baseline.copy()
        outside[5:20, 5:20] = 255
        self.assertFalse(detector.detect(outside).detected)
        inside = baseline.copy()
        inside[40:60, 40:60] = 255
        self.assertTrue(detector.detect(inside).detected)


if __name__ == "__main__":
    unittest.main()
