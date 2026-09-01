import pytest

from hornet_monitor.gallery import Gallery


def test_gallery_lists_event_and_persists_annotation(tmp_path):
    image = tmp_path / "events" / "2026-08-31" / "123000_000001" / "frame_000.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"test")
    second_frame = image.with_name("frame_001.jpg")
    second_frame.write_bytes(b"test")
    gallery = Gallery(image.parents[2], tmp_path / "annotations.jsonl")

    event = gallery.events()[0]
    assert event["image"] == "2026-08-31/123000_000001/frame_000.jpg"
    assert event["frames"] == [
        "2026-08-31/123000_000001/frame_000.jpg",
        "2026-08-31/123000_000001/frame_001.jpg",
    ]
    assert event["reviewed_frames"] == []
    assert not event["reviewed"]
    saved = gallery.annotate(
        {
            "image": "2026-08-31/123000_000001/frame_000.jpg",
            "label": "bee",
            "box": {"x": 1, "y": 2, "width": 3, "height": 4},
        }
    )
    assert saved["label"] == "bee"
    assert gallery.events()[0]["reviewed_frames"] == ["2026-08-31/123000_000001/frame_000.jpg"]
    assert gallery.events()[0]["animal_frames"] == ["2026-08-31/123000_000001/frame_000.jpg"]
    empty = gallery.annotate(
        {"image": "2026-08-31/123000_000001/frame_000.jpg", "label": "empty", "box": None}
    )
    assert empty["box"] is None
    goldfly = gallery.annotate(
        {
            "image": "2026-08-31/123000_000001/frame_000.jpg",
            "label": "goldfly",
            "box": {"x": 5, "y": 6, "width": 7, "height": 8},
        }
    )
    assert goldfly["label"] == "goldfly"
    fleshfly = gallery.annotate(
        {
            "image": "2026-08-31/123000_000001/frame_000.jpg",
            "label": "fleshfly",
            "box": {"x": 9, "y": 10, "width": 11, "height": 12},
        }
    )
    assert fleshfly["label"] == "fleshfly"
    blue_blowfly = gallery.annotate(
        {
            "image": "2026-08-31/123000_000001/frame_000.jpg",
            "label": "blue_blowfly",
            "box": {"x": 12, "y": 13, "width": 14, "height": 15},
        }
    )
    assert blue_blowfly["label"] == "blue_blowfly"
    assert gallery.events()[0]["reviewed"]
    gallery.delete_event("2026-08-31/123000_000001")
    assert gallery.events() == []
    assert (tmp_path / "annotations.jsonl").exists()


@pytest.mark.parametrize(
    "image_id",
    [
        "../secrets.jpg",
        "2026-08-31/123000_000001/../../secrets.jpg",
        "2026-08-31/123000_000001/other.jpg",
        "2026-08-31/123000_000001/frame_000.jpg/extra",
        "2026-08-31\\123000_000001\\frame_000.jpg",
    ],
)
def test_gallery_rejects_noncanonical_image_paths_before_filesystem_access(tmp_path, image_id):
    gallery = Gallery(tmp_path / "events", tmp_path / "annotations.jsonl")

    with pytest.raises(ValueError, match="Invalid event image path"):
        gallery.image_path(image_id)
