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
    assert event["labels"] == []
    assert not event["reviewed"]
    saved = gallery.annotate(
        {
            "image": "2026-08-31/123000_000001/frame_000.jpg",
            "label": "bee",
            "box": {"x": 1, "y": 2, "width": 3, "height": 4},
        }
    )
    assert saved["label"] == "bee"
    assert saved["source"] == "manual"
    assert gallery.events()[0]["reviewed_frames"] == ["2026-08-31/123000_000001/frame_000.jpg"]
    assert gallery.events()[0]["animal_frames"] == ["2026-08-31/123000_000001/frame_000.jpg"]
    assert gallery.events()[0]["labels"] == ["bee"]
    ant = gallery.annotate(
        {
            "image": "2026-08-31/123000_000001/frame_000.jpg",
            "label": "ant",
            "box": {"x": 5, "y": 6, "width": 7, "height": 8},
        }
    )
    assert ant["label"] == "ant"
    empty = gallery.annotate(
        {"image": "2026-08-31/123000_000001/frame_000.jpg", "label": "empty", "box": None}
    )
    assert empty["box"] is None
    goldfly = gallery.annotate(
        {
            "image": "2026-08-31/123000_000001/frame_000.jpg",
            "label": "goldfly",
            "box": {"x": 8, "y": 9, "width": 10, "height": 11},
        }
    )
    assert goldfly["label"] == "goldfly"
    fleshfly = gallery.annotate(
        {
            "image": "2026-08-31/123000_000001/frame_000.jpg",
            "label": "fleshfly",
            "box": {"x": 12, "y": 13, "width": 14, "height": 15},
        }
    )
    assert fleshfly["label"] == "fleshfly"
    blue_blowfly = gallery.annotate(
        {
            "image": "2026-08-31/123000_000001/frame_000.jpg",
            "label": "blue_blowfly",
            "box": {"x": 16, "y": 17, "width": 18, "height": 19},
        }
    )
    assert blue_blowfly["label"] == "blue_blowfly"
    assert gallery.events()[0]["reviewed"]
    assert gallery.mark_unannotated_frames_empty("2026-08-31/123000_000001") == [
        "2026-08-31/123000_000001/frame_001.jpg"
    ]
    assert gallery.annotations_for("2026-08-31/123000_000001/frame_001.jpg")[0]["label"] == "empty"
    gallery.delete_event("2026-08-31/123000_000001")
    assert gallery.events() == []
    assert (tmp_path / "annotations.jsonl").exists()


def test_gallery_exposes_night_preview_metadata_without_reading_images(tmp_path):
    image = tmp_path / "events" / "2026-09-01" / "123000_000001" / "frame_000.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"test")
    (image.parent / "event.json").write_text(
        '{"brightness": 12.5, "night_preview": true}', encoding="utf-8"
    )

    event = Gallery(image.parents[2], tmp_path / "annotations.jsonl").events()[0]

    assert event["brightness"] == 12.5
    assert event["night_preview"] is True


def test_gallery_filters_annotation_class_before_applying_the_event_limit(tmp_path):
    events = tmp_path / "events"
    newest = events / "2026-09-03" / "235959_000001" / "frame_000.jpg"
    uncertain = events / "2026-09-02" / "000000_000001" / "frame_000.jpg"
    newest.parent.mkdir(parents=True)
    uncertain.parent.mkdir(parents=True)
    newest.write_bytes(b"test")
    uncertain.write_bytes(b"test")
    gallery = Gallery(events, tmp_path / "annotations.jsonl")
    gallery.annotate(
        {
            "image": "2026-09-02/000000_000001/frame_000.jpg",
            "label": "uncertain",
            "box": {"x": 1, "y": 2, "width": 3, "height": 4},
        }
    )

    assert gallery.events(limit=1, label="uncertain")[0]["id"] == "2026-09-02/000000_000001"
    with pytest.raises(ValueError, match="Unknown annotation label"):
        gallery.events(label="not-a-class")


def test_gallery_can_return_all_events_for_a_narrow_server_side_review_queue(tmp_path):
    events = tmp_path / "events"
    for number in range(3):
        image = events / "2026-09-03" / f"12000{number}_000001" / "frame_000.jpg"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"test")
    gallery = Gallery(events, tmp_path / "annotations.jsonl")

    assert len(gallery.events(limit=1)) == 1
    assert len(gallery.events(limit=None)) == 3


def test_gallery_records_confirmed_model_suggestions_as_auditable_annotations(tmp_path):
    image = tmp_path / "events" / "2026-09-01" / "123000_000001" / "frame_000.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"test")
    gallery = Gallery(image.parents[2], tmp_path / "annotations.jsonl")

    saved = gallery.annotate(
        {
            "image": "2026-09-01/123000_000001/frame_000.jpg",
            "annotations": [
                {"label": "fleshfly", "box": {"x": 1, "y": 2, "width": 3, "height": 4}}
            ],
            "source": "model_confirmed",
        }
    )

    assert saved["annotations"][0]["source"] == "model_confirmed"
    with pytest.raises(ValueError, match="Unknown annotation source"):
        gallery.annotate(
            {
                "image": "2026-09-01/123000_000001/frame_000.jpg",
                "label": "empty",
                "box": None,
                "source": "untrusted",
            }
        )


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
