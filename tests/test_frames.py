import numpy as np
import pytest

from hornet_monitor.frames import crop_to_roi


def test_crop_to_roi_returns_only_the_requested_frame_area():
    frame = np.arange(10 * 12 * 3, dtype=np.uint8).reshape(10, 12, 3)

    cropped = crop_to_roi(frame, {"x": 3, "y": 2, "width": 5, "height": 4})

    assert cropped.shape == (4, 5, 3)
    assert np.array_equal(cropped, frame[2:6, 3:8])


def test_crop_to_roi_clamps_to_frame_edges_and_rejects_empty_result():
    frame = np.zeros((10, 12, 3), dtype=np.uint8)

    assert crop_to_roi(frame, {"x": 10, "y": 8, "width": 5, "height": 5}).shape == (2, 2, 3)
    with pytest.raises(ValueError, match="outside"):
        crop_to_roi(frame, {"x": 12, "y": 10, "width": 1, "height": 1})
