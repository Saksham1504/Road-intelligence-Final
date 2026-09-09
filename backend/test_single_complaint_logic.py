from main import build_complaint_row, seed_demo_complaints, Damage, SessionLocal


def test_demo_seed_is_disabled_by_default():
    with SessionLocal() as session:
        session.query(Damage).delete()
        session.commit()

    seed_demo_complaints()

    with SessionLocal() as session:
        assert session.query(Damage).count() == 0


def test_build_complaint_row_stores_one_complaint_for_multiple_detections():
    detections = [
        {"damage_type": "Pothole", "confidence": 0.91, "severity": "High", "bbox": [10, 20, 100, 200]},
        {"damage_type": "Pothole", "confidence": 0.87, "severity": "High", "bbox": [110, 30, 180, 240]},
        {"damage_type": "Crack", "confidence": 0.82, "severity": "Medium", "bbox": [50, 60, 140, 160]},
        {"damage_type": "Manhole", "confidence": 0.76, "severity": "Medium", "bbox": [180, 70, 260, 190]},
    ]

    complaint = build_complaint_row(
        detections=detections,
        latitude=28.6139,
        longitude=77.2090,
        address="Ram Nagar, Delhi, India",
        original_image_url="/uploads/citizen.jpg",
        annotated_image_url="/uploads/annotated.jpg",
        status="Pending",
        verification_status="Pending Verification",
        report_count=1,
    )

    assert complaint["damage_type"] == "Multiple"
    assert complaint["confidence"] == 0.91
    assert complaint["severity"] == "High"
    assert complaint["report_count"] == 1
    assert len(complaint["detections"]) == 4
    assert [item["damage_type"] for item in complaint["detections"]] == [
        "Pothole",
        "Pothole",
        "Crack",
        "Manhole",
    ]
