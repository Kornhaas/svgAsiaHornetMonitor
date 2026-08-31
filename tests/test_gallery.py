from hornet_monitor.gallery import Gallery


def test_gallery_lists_event_and_persists_annotation(tmp_path):
    image = tmp_path / "events" / "2026-08-31" / "123000_000001" / "frame_000.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"test")
    gallery = Gallery(image.parents[2], tmp_path / "annotations.jsonl")

    assert gallery.events()[0]["image"] == "2026-08-31/123000_000001/frame_000.jpg"
    saved = gallery.annotate(
        {
            "image": "2026-08-31/123000_000001/frame_000.jpg",
            "label": "bee",
            "box": {"x": 1, "y": 2, "width": 3, "height": 4},
        }
    )
    assert saved["label"] == "bee"
    empty = gallery.annotate(
        {"image": "2026-08-31/123000_000001/frame_000.jpg", "label": "empty", "box": None}
    )
    assert empty["box"] is None
    assert (tmp_path / "annotations.jsonl").exists()
