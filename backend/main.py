from pathlib import Path
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import math
import os
import uuid
from collections import Counter

import cv2
import requests
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, inspect, text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from ultralytics import YOLO

BASE = Path(__file__).resolve().parent
ROAD_DAMAGE_MODEL_PATH = BASE.parent / "road_damage" / "runs" / "detect" / "runs" / "detect" / "road_damage" / "weights" / "best.pt"
DEFAULT_MODEL_PATH = ROAD_DAMAGE_MODEL_PATH if ROAD_DAMAGE_MODEL_PATH.exists() else BASE / "model" / "best.pt"
MODEL_PATH = Path(os.getenv("ROAD_DAMAGE_MODEL", str(DEFAULT_MODEL_PATH)))
UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MODEL_CONFIDENCE = 0.10
MODEL_IOU = 0.45
MODEL_MAX_DETECTIONS = 50
TILE_GRID = 2
TILE_OVERLAP = 0.15
MODEL_IMAGE_SIZE = 1280
FINAL_CONFIDENCE = 0.15
DUPLICATE_RADIUS_METERS = 50
DUPLICATE_WINDOW_HOURS = 24

# -----------------------------
# APP
# -----------------------------
app = FastAPI(title="Road Intelligence API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+):517[34]$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# -----------------------------
# DATABASE
# -----------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://sih_admin:sih12345@localhost:5432/road_intelligence",
)
engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Damage(Base):
    __tablename__ = "damages"

    id = Column(Integer, primary_key=True)
    damage_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    severity = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String, nullable=True)
    status = Column(String, default="Pending")
    verification_status = Column(String, default="Pending Verification")
    image_url = Column(String)
    original_image_url = Column(String, nullable=True)
    annotated_image_url = Column(String, nullable=True)
    related_report_images = Column(String, nullable=True)
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    latest_reported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(String, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    officer_action = Column(String, nullable=True)
    report_count = Column(Integer, default=1, nullable=False)
    detections = relationship(
        "ComplaintDetection",
        cascade="all, delete-orphan",
        foreign_keys="[ComplaintDetection.complaint_id]",
        order_by="ComplaintDetection.id",
    )
    reports = relationship("ComplaintReport", cascade="all, delete-orphan", order_by="ComplaintReport.id")


class ComplaintReport(Base):
    __tablename__ = "complaint_reports"

    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("damages.id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String, nullable=True)
    original_image_url = Column(String, nullable=True)
    annotated_image_url = Column(String, nullable=True)
    image_hash = Column(String, nullable=True, index=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    detections = relationship(
        "ComplaintDetection",
        foreign_keys="[ComplaintDetection.report_id]",
        order_by="ComplaintDetection.id",
    )


class ComplaintDetection(Base):
    __tablename__ = "complaint_detections"

    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("damages.id"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("complaint_reports.id"), nullable=True, index=True)
    damage_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    x1 = Column(Integer, nullable=False)
    y1 = Column(Integer, nullable=False)
    x2 = Column(Integer, nullable=False)
    y2 = Column(Integer, nullable=False)
    severity = Column(String, nullable=False)


class ComplaintHistory(Base):
    __tablename__ = "complaint_history"

    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, nullable=False)
    damage_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    severity = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String, nullable=True)
    original_image_url = Column(String, nullable=True)
    annotated_image_url = Column(String, nullable=True)
    related_report_images = Column(String, nullable=True)
    status = Column(String, default="Completed")
    verification_status = Column(String, default="Accepted")
    final_status = Column(String, nullable=False)
    rejection_reason = Column(String, nullable=True)
    report_count = Column(Integer, default=1, nullable=False)
    detected_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)
    completed_by = Column(String, nullable=True)
    rejected_by = Column(String, nullable=True)
    archived_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    detections = relationship("ComplaintHistoryDetection", cascade="all, delete-orphan", order_by="ComplaintHistoryDetection.id")


class ComplaintHistoryDetection(Base):
    __tablename__ = "complaint_history_detections"

    id = Column(Integer, primary_key=True)
    history_id = Column(Integer, ForeignKey("complaint_history.id"), nullable=False, index=True)
    damage_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    x1 = Column(Integer, nullable=False)
    y1 = Column(Integer, nullable=False)
    x2 = Column(Integer, nullable=False)
    y2 = Column(Integer, nullable=False)
    severity = Column(String, nullable=False)


Base.metadata.create_all(engine)


def seed_demo_complaints():
    import os

    if os.getenv("ENABLE_DEMO_DATA", "0").lower() not in {"1", "true", "yes", "on"}:
        return

    with SessionLocal() as session:
        if session.query(Damage).count() > 0:
            return
        demo_rows = [
            ("pothole", 0.92, "Critical", 28.6139, 77.2090, "Near Connaught Place, New Delhi", "Verified", "/uploads/demo_1.jpg"),
            ("crack", 0.81, "High", 28.6128, 77.2163, "Near India Gate, New Delhi", "Pending", "/uploads/demo_2.jpg"),
            ("manhole", 0.74, "Medium", 28.6210, 77.2130, "Near Sarojini Nagar, New Delhi", "Assigned", "/uploads/demo_3.jpg"),
        ]
        for damage_type, confidence, severity, latitude, longitude, address, status, image_url in demo_rows:
            session.add(
                Damage(
                    damage_type=damage_type,
                    confidence=confidence,
                    severity=severity,
                    latitude=latitude,
                    longitude=longitude,
                    address=address,
                    status=status,
                    image_url=image_url,
                )
            )
        session.commit()


# SQLAlchemy creates the complete complaint schema for PostgreSQL and fresh SQLite databases.

# -----------------------------
# AI MODEL
# -----------------------------
model = None
model_error = None
if MODEL_PATH.exists():
    try:
        model = YOLO(str(MODEL_PATH))
    except Exception as exc:
        model_error = str(exc)
else:
    model_error = f"YOLO model not found: {MODEL_PATH}"

# -----------------------------
# DEMO GOVERNMENT AUTH
# Change these before any real deployment.
# -----------------------------
GOV_USERNAME = "gov_admin"
GOV_PASSWORD = "SIH@2026"
AUTH_SECRET = "road-intelligence-sih-demo-change-this-secret"
TOKEN_TTL_SECONDS = 8 * 60 * 60


def make_token(username: str) -> str:
    payload = {
        "sub": username,
        "role": "government",
        "exp": int(datetime.now(timezone.utc).timestamp()) + TOKEN_TTL_SECONDS,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    body = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def require_government(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Government login required")

    token = authorization.split(" ", 1)[1].strip()
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("bad signature")
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        if payload.get("role") != "government":
            raise ValueError("wrong role")
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired government session")


# -----------------------------
# DB DEPENDENCY
# -----------------------------
def db():
    d = SessionLocal()
    try:
        yield d
    finally:
        d.close()


# -----------------------------
# LOCATION / SEVERITY
# -----------------------------
def reverse_geocode(latitude: float, longitude: float) -> str:
    """Convert GPS coordinates into a human-friendly place address."""
    fallback = f"GPS: {latitude:.6f}, {longitude:.6f}"
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "zoom": 18,
                "addressdetails": 1,
                "namedetails": 1,
            },
            headers={"User-Agent": "RoadIntelligence-SIH-Prototype/1.0"},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            return fallback

        address = data.get("address") or {}
        road = address.get("road") or address.get("pedestrian") or address.get("service")
        locality = (
            address.get("neighbourhood")
            or address.get("suburb")
            or address.get("village")
            or address.get("hamlet")
            or address.get("town")
            or address.get("city")
            or address.get("municipality")
        )
        city = address.get("city") or address.get("town") or address.get("municipality") or address.get("village")
        state = address.get("state") or address.get("province") or address.get("state_district")
        country = address.get("country")

        place_parts = [part for part in [road, locality, city, state, country] if part]
        if place_parts:
            return ", ".join(place_parts[:4])

        return data.get("display_name") or fallback
    except Exception:
        return fallback + " (address lookup unavailable)"


def severity(confidence: float, area_ratio: float) -> str:
    # Prototype prioritisation rule; not a civil-engineering safety standard.
    score = 0.55 * confidence + 0.45 * min(area_ratio * 4, 1.0)
    if score >= 0.72:
        return "Critical"
    if score >= 0.52:
        return "High"
    if score >= 0.32:
        return "Medium"
    return "Low"


def distance_meters(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    earth_radius = 6_371_000
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    return earth_radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def find_existing_complaint(
    d: Session,
    detections: list[dict],
    image_hash: str,
    latitude: float,
    longitude: float,
    now: datetime,
):
    window_start = now.replace(tzinfo=None) - timedelta(hours=DUPLICATE_WINDOW_HOURS)
    candidates = d.query(Damage).filter(
        Damage.latest_reported_at >= window_start,
        Damage.status.notin_(["Completed", "Rejected"]),
    ).all()
    nearby = [
        row for row in candidates
        if distance_meters(latitude, longitude, row.latitude, row.longitude) <= DUPLICATE_RADIUS_METERS
    ]
    exact_image_match = next(
        (
            row for row in nearby
            if any(report.image_hash == image_hash for report in (row.reports or []))
        ),
        None,
    )
    if exact_image_match is not None:
        return exact_image_match

    submitted_types = {item["damage_type"] for item in detections}
    for row in nearby:
        existing_types = {item.damage_type for item in (row.detections or [])}
        if "Multiple" in {row.damage_type, *existing_types} or submitted_types.intersection(existing_types):
            return row
    return None


def parse_related_images(value: str | None):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [item for item in parsed if item]
    except (TypeError, ValueError):
        pass
    return []


def append_related_image(row: Damage, image_url: str | None):
    if not image_url:
        return
    urls = parse_related_images(row.related_report_images)
    if image_url not in urls:
        urls.append(image_url)
        row.related_report_images = json.dumps(urls)


def serialize_detection(item):
    if item is None:
        return None
    return {
        "id": item.id,
        "complaint_id": item.complaint_id,
        "damage_type": item.damage_type,
        "confidence": float(item.confidence),
        "severity": item.severity,
        "x1": item.x1,
        "y1": item.y1,
        "x2": item.x2,
        "y2": item.y2,
        "bbox": [item.x1, item.y1, item.x2, item.y2],
        "report_id": item.report_id,
    }


def serialize_history_detection(item):
    if item is None:
        return None
    return {
        "id": item.id,
        "damage_type": item.damage_type,
        "confidence": float(item.confidence),
        "severity": item.severity,
        "x1": item.x1,
        "y1": item.y1,
        "x2": item.x2,
        "y2": item.y2,
        "bbox": [item.x1, item.y1, item.x2, item.y2],
    }


def serialize_report(report):
    return {
        "id": report.id,
        "complaint_id": report.complaint_id,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "address": report.address,
        "original_image_url": report.original_image_url,
        "annotated_image_url": report.annotated_image_url,
        "same_image": bool(report.image_hash),
        "submitted_at": report.submitted_at.isoformat() if report.submitted_at else None,
        "detections": [serialize_detection(item) for item in report.detections],
    }


def serialize_damage(row: Damage):
    if row is None:
        return None
    active_image_url = row.annotated_image_url or row.image_url or row.original_image_url
    detections = [serialize_detection(item) for item in (row.detections or [])]
    damage_breakdown = [
        {"damage_type": damage_type, "count": count}
        for damage_type, count in Counter(item["damage_type"] for item in detections).most_common()
    ]
    return {
        "id": row.id,
        "damage_type": row.damage_type,
        "confidence": row.confidence,
        "severity": row.severity,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "address": row.address,
        "status": row.status,
        "verification_status": row.verification_status or "Pending Verification",
        "image_url": active_image_url,
        "annotated_image_url": row.annotated_image_url or row.image_url or row.original_image_url,
        "original_image_url": row.original_image_url or row.image_url,
        "related_report_images": parse_related_images(row.related_report_images),
        "detected_at": row.detected_at.isoformat() if row.detected_at else None,
        "latest_reported_at": row.latest_reported_at.isoformat() if row.latest_reported_at else None,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
        "verified_by": row.verified_by,
        "rejected_at": row.rejected_at.isoformat() if row.rejected_at else None,
        "rejected_by": row.rejected_by,
        "rejection_reason": row.rejection_reason,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "completed_by": row.completed_by,
        "archived_at": row.archived_at.isoformat() if row.archived_at else None,
        "report_count": row.report_count or 1,
        "detections": detections,
        "detection_count": len(detections),
        "damage_breakdown": damage_breakdown,
        "reports": [serialize_report(report) for report in (row.reports or [])],
    }


def build_complaint_row(
    detections: list[dict],
    latitude: float,
    longitude: float,
    address: str,
    original_image_url: str,
    annotated_image_url: str,
    status: str = "Pending",
    verification_status: str = "Pending Verification",
    report_count: int = 1,
):
    if not detections:
        return {
            "damage_type": "Multiple",
            "confidence": 0.0,
            "severity": "Low",
            "latitude": latitude,
            "longitude": longitude,
            "address": address,
            "status": status,
            "verification_status": verification_status,
            "image_url": annotated_image_url,
            "original_image_url": original_image_url,
            "annotated_image_url": annotated_image_url,
            "report_count": report_count,
            "detections": [],
        }

    ordered = sorted(detections, key=lambda item: item["confidence"], reverse=True)
    severity_levels = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    highest_severity = max((item["severity"] for item in ordered), key=lambda value: severity_levels.get(value, 0))
    damage_type = "Multiple" if len(detections) > 1 else ordered[0]["damage_type"]
    return {
        "damage_type": damage_type,
        "confidence": float(ordered[0]["confidence"]),
        "severity": highest_severity,
        "latitude": latitude,
        "longitude": longitude,
        "address": address,
        "status": status,
        "image_url": annotated_image_url,
        "original_image_url": original_image_url,
        "annotated_image_url": annotated_image_url,
        "report_count": report_count,
        "detections": [
            {
                "complaint_id": None,
                "damage_type": item["damage_type"],
                "confidence": float(item["confidence"]),
                "severity": item["severity"],
                "x1": item["bbox"][0],
                "y1": item["bbox"][1],
                "x2": item["bbox"][2],
                "y2": item["bbox"][3],
                "bbox": item["bbox"],
            }
            for item in ordered
        ],
    }


def save_complaint_detections(d: Session, complaint_id: int, detections: list[dict], report_id: int | None = None):
    if not detections:
        return
    for item in detections:
        d.add(
            ComplaintDetection(
                complaint_id=complaint_id,
                report_id=report_id,
                damage_type=item["damage_type"],
                confidence=float(item["confidence"]),
                x1=int(item["bbox"][0]),
                y1=int(item["bbox"][1]),
                x2=int(item["bbox"][2]),
                y2=int(item["bbox"][3]),
                severity=item["severity"],
            )
        )


def create_history_records_for_complaint(d: Session, row: Damage, final_status: str, reason: str | None = None):
    existing = d.query(ComplaintHistory).filter(ComplaintHistory.complaint_id == row.id, ComplaintHistory.final_status == final_status).first()
    if existing is None:
        existing = ComplaintHistory(
            complaint_id=row.id,
            damage_type=row.damage_type,
            confidence=row.confidence,
            severity=row.severity,
            latitude=row.latitude,
            longitude=row.longitude,
            address=row.address,
            original_image_url=row.original_image_url or row.image_url,
            annotated_image_url=row.annotated_image_url or row.image_url,
            related_report_images=row.related_report_images,
            status=row.status,
            verification_status=row.verification_status or "Accepted",
            final_status=final_status,
            rejection_reason=reason,
            report_count=row.report_count or 1,
            detected_at=row.detected_at,
            verified_at=row.verified_at,
            completed_at=row.completed_at,
            rejected_at=row.rejected_at,
            verified_by=row.verified_by,
            completed_by=row.completed_by,
            rejected_by=row.rejected_by,
            archived_at=datetime.now(timezone.utc),
        )
        d.add(existing)
        d.flush()
    else:
        existing.damage_type = row.damage_type
        existing.confidence = row.confidence
        existing.severity = row.severity
        existing.latitude = row.latitude
        existing.longitude = row.longitude
        existing.address = row.address
        existing.original_image_url = row.original_image_url or row.image_url
        existing.annotated_image_url = row.annotated_image_url or row.image_url
        existing.related_report_images = row.related_report_images
        existing.status = row.status
        existing.verification_status = row.verification_status or "Accepted"
        existing.final_status = final_status
        existing.rejection_reason = reason or existing.rejection_reason
        existing.report_count = row.report_count or 1
        existing.detected_at = row.detected_at
        existing.verified_at = row.verified_at
        existing.completed_at = row.completed_at
        existing.rejected_at = row.rejected_at
        existing.verified_by = row.verified_by
        existing.completed_by = row.completed_by
        existing.rejected_by = row.rejected_by
        existing.archived_at = datetime.now(timezone.utc)

    for history_detection in list(existing.detections):
        d.delete(history_detection)
    for detection in d.query(ComplaintDetection).filter(ComplaintDetection.complaint_id == row.id).all():
        existing.detections.append(
            ComplaintHistoryDetection(
                damage_type=detection.damage_type,
                confidence=float(detection.confidence),
                x1=int(detection.x1),
                y1=int(detection.y1),
                x2=int(detection.x2),
                y2=int(detection.y2),
                severity=detection.severity,
            )
        )
    return existing


def get_active_damages_query(d: Session):
    return d.query(Damage).filter(Damage.status.notin_(["Completed", "Rejected"]))


def archive_complaint(d: Session, row: Damage, final_status: str, reason: str | None = None, officer_name: str | None = None):
    if row is None:
        return None
    if row.status == final_status and row.archived_at:
        return None

    existing = create_history_records_for_complaint(d, row, final_status, reason)

    row.archived_at = datetime.now(timezone.utc)
    if final_status == "Completed":
        row.status = "Completed"
        row.completed_at = row.completed_at or datetime.now(timezone.utc)
        row.completed_by = officer_name or row.completed_by
    else:
        row.status = "Rejected"
        row.rejected_at = row.rejected_at or datetime.now(timezone.utc)
        row.rejected_by = officer_name or row.rejected_by
        row.rejection_reason = reason or row.rejection_reason
    row.officer_action = final_status
    d.commit()
    return existing


def predict_damage(image, width: int, height: int):
    prediction = model.predict(
        source=image,
        conf=0.01,
        iou=0.45,
        max_det=20,
        imgsz=1280,
        verbose=False,
    )[0]

    detections = []

    for box in prediction.boxes:
        cls_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        x1 = max(0, min(width, int(x1)))
        y1 = max(0, min(height, int(y1)))
        x2 = max(0, min(width, int(x2)))
        y2 = max(0, min(height, int(y2)))

        if x2 <= x1 or y2 <= y1:
            continue

        detections.append({
            "class_id": cls_id,
            "confidence": confidence,
            "bbox": [x1, y1, x2, y2],
        })

    return sorted(
        detections,
        key=lambda item: item["confidence"],
        reverse=True
    )

    # -------------------------------------------------
    # 2. TILED INFERENCE
    # -------------------------------------------------
    if TILE_GRID > 1:
        tile_w = int(width / TILE_GRID)
        tile_h = int(height / TILE_GRID)

        overlap_w = int(tile_w * TILE_OVERLAP)
        overlap_h = int(tile_h * TILE_OVERLAP)

        for row in range(TILE_GRID):
            for col in range(TILE_GRID):

                x_start = max(0, col * tile_w - overlap_w)
                y_start = max(0, row * tile_h - overlap_h)

                x_end = min(
                    width,
                    (col + 1) * tile_w + overlap_w
                )

                y_end = min(
                    height,
                    (row + 1) * tile_h + overlap_h
                )

                tile = image[y_start:y_end, x_start:x_end]

                if tile.size == 0:
                    continue

                tile_prediction = model.predict(
                    source=tile,
                    conf=MODEL_CONFIDENCE,
                    iou=MODEL_IOU,
                    max_det=MODEL_MAX_DETECTIONS,
                    imgsz=MODEL_IMAGE_SIZE,
                    verbose=False,
                )[0]

                for box in tile_prediction.boxes:
                    cls_id = int(box.cls[0].item())
                    confidence = float(box.conf[0].item())

                    tx1, ty1, tx2, ty2 = box.xyxy[0].tolist()

                    # Convert tile coordinates back
                    # to original image coordinates.
                    x1 = int(tx1 + x_start)
                    y1 = int(ty1 + y_start)
                    x2 = int(tx2 + x_start)
                    y2 = int(ty2 + y_start)

                    x1 = max(0, min(width, x1))
                    y1 = max(0, min(height, y1))
                    x2 = max(0, min(width, x2))
                    y2 = max(0, min(height, y2))

                    if x2 <= x1 or y2 <= y1:
                        continue

                    all_detections.append({
                        "class_id": cls_id,
                        "confidence": confidence,
                        "bbox": [x1, y1, x2, y2],
                    })

    # -------------------------------------------------
    # 3. SORT BY CONFIDENCE
    # -------------------------------------------------
    all_detections.sort(
        key=lambda item: item["confidence"],
        reverse=True
    )

    # -------------------------------------------------
    # 4. REMOVE DUPLICATE BOXES
    # -------------------------------------------------
    def calculate_iou(box_a, box_b):
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)

        intersection = inter_w * inter_h

        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)

        union = area_a + area_b - intersection

        if union <= 0:
            return 0.0

        return intersection / union

    final_detections = []

    for candidate in all_detections:

        # Final confidence filter.
        if candidate["confidence"] < FINAL_CONFIDENCE:
            continue

        duplicate = False

        for selected in final_detections:

            # Only compare boxes belonging to
            # the same damage class.
            if candidate["class_id"] != selected["class_id"]:
                continue

            iou = calculate_iou(
                candidate["bbox"],
                selected["bbox"]
            )

            if iou >= 0.45:
                duplicate = True
                break

        if not duplicate:
            final_detections.append(candidate)

        if len(final_detections) >= MODEL_MAX_DETECTIONS:
            break

    # -------------------------------------------------
    # 5. FINAL SORT
    # -------------------------------------------------
    return sorted(
        final_detections,
        key=lambda item: item["confidence"],
        reverse=True
    )


# -----------------------------
# PUBLIC ENDPOINTS
# -----------------------------
@app.get("/")
def root():
    return {
        "message": "Road Intelligence API running",
        "model": MODEL_PATH.name,
        "model_loaded": model is not None,
        "model_error": model_error,
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok" if model is not None else "degraded",
        "model_loaded": model is not None,
        "model_path": str(MODEL_PATH),
        "model_error": model_error,
        "inference": {
            "confidence": MODEL_CONFIDENCE,
            "iou": MODEL_IOU,
            "max_det": MODEL_MAX_DETECTIONS,
        },
    }


@app.post("/api/government/login")
def government_login(username: str = Form(...), password: str = Form(...)):
    if not hmac.compare_digest(username, GOV_USERNAME) or not hmac.compare_digest(password, GOV_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid government credentials")
    return {
        "access_token": make_token(username),
        "token_type": "bearer",
        "role": "government",
        "expires_in": TOKEN_TTL_SECONDS,
    }


@app.post("/api/detect")
async def detect(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    location_accuracy_m: float | None = Form(default=None),
    address_override: str | None = Form(default=None),
    d: Session = Depends(db),
):
    if model is None:
        raise HTTPException(503, f"YOLO model is unavailable: {model_error}")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(400, "Invalid GPS coordinates")
    if location_accuracy_m is not None and not (0 <= location_accuracy_m <= 100000):
        raise HTTPException(400, "Invalid GPS accuracy")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty image")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image is too large. Maximum 10 MB.")

    suffix = Path(file.filename or "image.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"

    original_name = f"{uuid.uuid4().hex}{suffix}"
    original_path = UPLOAD_DIR / original_name
    original_path.write_bytes(content)
    image_hash = hashlib.sha256(content).hexdigest()

    image = cv2.imread(str(original_path))
    if image is None:
        raise HTTPException(400, "The uploaded file is not a valid image")

    h, w = image.shape[:2]
    detections = []
    names = model.names

    for item in predict_damage(image, w, h):
        cls_id = item["class_id"]
        conf = item["confidence"]
        x1, y1, x2, y2 = item["bbox"]
        area_ratio = max(0, x2 - x1) * max(0, y2 - y1) / float(w * h)
        label = names[cls_id] if isinstance(names, dict) else names[cls_id]
        sev = severity(conf, area_ratio)
        detections.append(
            {
                "damage_type": str(label),
                "confidence": conf,
                "severity": sev,
                "bbox": [x1, y1, x2, y2],
            }
        )
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 180, 80), 3)
        cv2.putText(
            image,
            f"{label} {conf:.0%} | {sev}",
            (x1, max(25, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 180, 80),
            2,
        )

    annotated_name = f"annotated_{uuid.uuid4().hex}.jpg"
    cv2.imwrite(str(UPLOAD_DIR / annotated_name), image)
    original_image_url = f"/uploads/{original_name}"
    annotated_image_url = f"/uploads/{annotated_name}"
    address = address_override.strip() if address_override and address_override.strip() else reverse_geocode(latitude, longitude)

    now = datetime.now(timezone.utc)
    complaint_summary = build_complaint_row(
        detections=detections,
        latitude=latitude,
        longitude=longitude,
        address=address,
        original_image_url=original_image_url,
        annotated_image_url=annotated_image_url,
        status="Pending",
        verification_status="Pending Verification",
        report_count=1,
    )
    primary = max(detections, key=lambda item: item["confidence"]) if detections else None
    complaint_id = None
    linked_ids = []
    created_ids = []

    if primary:
        existing = find_existing_complaint(d, detections, image_hash, latitude, longitude, now)
        if existing is not None:
            existing.report_count = (existing.report_count or 1) + 1
            existing.latest_reported_at = now
            existing.confidence = max(float(existing.confidence or 0.0), float(primary["confidence"]))
            existing.severity = complaint_summary["severity"]
            existing.damage_type = "Multiple" if len(detections) > 1 else existing.damage_type or complaint_summary["damage_type"]
            existing.annotated_image_url = annotated_image_url
            existing.original_image_url = existing.original_image_url or original_image_url
            append_related_image(existing, original_image_url)
            append_related_image(existing, annotated_image_url)
            existing.image_url = existing.annotated_image_url or existing.image_url or annotated_image_url
            complaint_id = existing.id
            linked_ids.append(existing.id)
            report = ComplaintReport(
                complaint_id=existing.id,
                latitude=latitude,
                longitude=longitude,
                address=address,
                original_image_url=original_image_url,
                annotated_image_url=annotated_image_url,
                image_hash=image_hash,
                submitted_at=now,
            )
            d.add(report)
            d.flush()
            save_complaint_detections(d, existing.id, complaint_summary["detections"], report.id)
        else:
            row = Damage(
                damage_type=complaint_summary["damage_type"],
                confidence=float(complaint_summary["confidence"]),
                severity=complaint_summary["severity"],
                latitude=latitude,
                longitude=longitude,
                address=address,
                status="Pending",
                verification_status="Pending Verification",
                image_url=annotated_image_url,
                original_image_url=original_image_url,
                annotated_image_url=annotated_image_url,
                detected_at=now,
                latest_reported_at=now,
                report_count=1,
            )
            d.add(row)
            d.flush()
            complaint_id = row.id
            created_ids.append(row.id)
            report = ComplaintReport(
                complaint_id=row.id,
                latitude=latitude,
                longitude=longitude,
                address=address,
                original_image_url=original_image_url,
                annotated_image_url=annotated_image_url,
                image_hash=image_hash,
                submitted_at=now,
            )
            d.add(report)
            d.flush()
            save_complaint_detections(d, row.id, complaint_summary["detections"], report.id)

    d.commit()

    complaint_ids = list(dict.fromkeys(created_ids + linked_ids))
    return {
        "count": len(detections),
        "complaint_id": complaint_id,
        "complaint_ids": complaint_ids,
        "created_complaint_ids": created_ids,
        "linked_complaint_ids": linked_ids,
        "detections": complaint_summary["detections"],
        "image_url": annotated_image_url,
        "original_image_url": original_image_url,
        "annotated_image_url": annotated_image_url,
        "latitude": latitude,
        "longitude": longitude,
        "location_accuracy_m": location_accuracy_m,
        "address": address,
        "complaint_registered": bool(complaint_id),
        "duplicate_policy": {
            "radius_m": DUPLICATE_RADIUS_METERS,
            "window_hours": DUPLICATE_WINDOW_HOURS,
            "action": "link_existing_complaint",
        },
        "inference": {
            "confidence": MODEL_CONFIDENCE,
            "iou": MODEL_IOU,
            "tile_grid": TILE_GRID,
            "tile_overlap": TILE_OVERLAP,
        },
    }


# -----------------------------
# GOVERNMENT-ONLY ENDPOINTS
# -----------------------------
@app.get("/api/damages")
def damages(_: dict = Depends(require_government), d: Session = Depends(db)):
    rows = get_active_damages_query(d).order_by(Damage.id.desc()).all()
    return [serialize_damage(row) for row in rows]


@app.get("/api/damages/{damage_id}")
def get_damage(damage_id: int, _: dict = Depends(require_government), d: Session = Depends(db)):
    row = d.query(Damage).filter(Damage.id == damage_id).first()
    if not row:
        raise HTTPException(404, "Complaint not found")
    return serialize_damage(row)


@app.get("/api/damages/{damage_id}/image")
def get_damage_evidence(damage_id: int, _: dict = Depends(require_government), d: Session = Depends(db)):
    row = d.query(Damage).filter(Damage.id == damage_id).first()
    if not row:
        raise HTTPException(404, "Complaint not found")
    return {
        "complaint_id": row.id,
        "damage_type": row.damage_type,
        "confidence": row.confidence,
        "severity": row.severity,
        "address": row.address,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "report_count": row.report_count or 1,
        "original_image_url": row.original_image_url or row.image_url,
        "annotated_image_url": row.annotated_image_url or row.image_url,
        "related_report_images": parse_related_images(row.related_report_images),
        "detections": [serialize_detection(item) for item in (row.detections or [])],
        "detection_count": len(row.detections or []),
    }


@app.get("/api/damages/{damage_id}/reports")
def get_damage_reports(damage_id: int, _: dict = Depends(require_government), d: Session = Depends(db)):
    row = d.query(Damage).filter(Damage.id == damage_id).first()
    if not row:
        raise HTTPException(404, "Complaint not found")
    report_images = parse_related_images(row.related_report_images)
    return {
        "complaint_id": row.id,
        "report_count": row.report_count or 1,
        "master_complaint": serialize_damage(row),
        "related_report_images": report_images,
        "detections": [serialize_detection(item) for item in (row.detections or [])],
    }


@app.post("/api/damages/{damage_id}/verify")
def verify_damage(
    damage_id: int,
    payload: dict | None = Body(default=None),
    _: dict = Depends(require_government),
    d: Session = Depends(db),
):
    row = d.query(Damage).filter(Damage.id == damage_id).first()
    if not row:
        raise HTTPException(404, "Complaint not found")
    if row.status in {"Completed", "Rejected"}:
        raise HTTPException(400, "This complaint is already archived in history.")
    row.verification_status = "Accepted"
    row.status = "In Progress"
    row.verified_at = datetime.now(timezone.utc)
    row.verified_by = _.get("sub") or "government_officer"
    row.officer_action = "verified"
    d.commit()
    d.refresh(row)
    return {"message": f"Complaint #{row.id} verified successfully.", "complaint": serialize_damage(row)}


@app.post("/api/damages/{damage_id}/reject")
def reject_damage(
    damage_id: int,
    payload: dict | None = Body(default=None),
    _: dict = Depends(require_government),
    d: Session = Depends(db),
):
    row = d.query(Damage).filter(Damage.id == damage_id).first()
    if not row:
        raise HTTPException(404, "Complaint not found")
    if row.status in {"Completed", "Rejected"}:
        raise HTTPException(400, "This complaint is already archived in history.")
    if payload is None:
        raise HTTPException(400, "A rejection reason is required.")
    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(400, "A rejection reason is required.")

    row.verification_status = "Rejected"
    row.status = "Rejected"
    row.rejected_at = datetime.now(timezone.utc)
    row.rejected_by = _.get("sub") or "government_officer"
    row.rejection_reason = reason
    row.officer_action = "rejected"
    archive_complaint(d, row, "Rejected", reason, row.rejected_by)
    d.commit()
    d.refresh(row)
    return {"message": f"Complaint #{row.id} rejected successfully.", "complaint": serialize_damage(row)}


@app.get("/api/complaints/history")
def complaint_history(_: dict = Depends(require_government), d: Session = Depends(db)):
    rows = d.query(ComplaintHistory).order_by(ComplaintHistory.archived_at.desc()).all()
    result = []
    for row in rows:
        archived_complaint = d.query(Damage).filter(Damage.id == row.complaint_id).first()
        result.append({
            "id": row.id,
            "complaint_id": row.complaint_id,
            "damage_type": row.damage_type,
            "confidence": row.confidence,
            "severity": row.severity,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "address": row.address,
            "final_status": row.final_status,
            "status": row.status,
            "verification_status": row.verification_status,
            "image_url": row.annotated_image_url or row.original_image_url,
            "annotated_image_url": row.annotated_image_url or row.original_image_url,
            "original_image_url": row.original_image_url,
            "related_report_images": parse_related_images(row.related_report_images),
            "report_count": row.report_count or 1,
            "detected_at": row.detected_at.isoformat() if row.detected_at else None,
            "verified_at": row.verified_at.isoformat() if row.verified_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "rejected_at": row.rejected_at.isoformat() if row.rejected_at else None,
            "rejection_reason": row.rejection_reason,
            "archived_at": row.archived_at.isoformat() if row.archived_at else None,
            "verified_by": row.verified_by,
            "completed_by": row.completed_by,
            "rejected_by": row.rejected_by,
            "detections": [serialize_history_detection(item) for item in (row.detections or [])],
            "detection_count": len(row.detections or []),
            "reports": [serialize_report(report) for report in (archived_complaint.reports or [])] if archived_complaint else [],
        })
    return result


@app.patch("/api/damages/{damage_id}/status")
def update_status(
    damage_id: int,
    status: str,
    _: dict = Depends(require_government),
    d: Session = Depends(db),
):
    allowed = {"Pending", "In Progress", "Completed"}
    if status not in allowed:
        raise HTTPException(400, "Invalid status")
    row = d.query(Damage).filter(Damage.id == damage_id).first()
    if not row:
        raise HTTPException(404, "Complaint not found")
    if row.status in {"Completed", "Rejected"}:
        raise HTTPException(400, "This complaint is already archived in the history log.")
    if row.verification_status != "Accepted" and status != "Pending":
        raise HTTPException(403, "Complaint must be accepted before status changes can be made.")
    if status == "In Progress" and row.status != "Pending":
        raise HTTPException(400, "Complaint must be Pending before work can start.")
    if status == "Completed" and row.status != "In Progress":
        raise HTTPException(400, "Complaint must be In Progress before it can be completed.")

    row.status = status
    row.officer_action = status.lower().replace(" ", "_")
    if status == "Pending":
        row.verification_status = "Accepted"
        row.verified_at = row.verified_at or datetime.now(timezone.utc)
    elif status == "In Progress":
        row.verification_status = "Accepted"
    elif status == "Completed":
        row.completed_at = datetime.now(timezone.utc)
        row.completed_by = _.get("sub") or "government_officer"
        row.verification_status = "Accepted"
        archive_complaint(d, row, "Completed", None, row.completed_by)
    d.commit()
    d.refresh(row)
    return {"message": f"Complaint #{row.id} updated to {status}.", "complaint": serialize_damage(row)}


@app.get("/api/dashboard/stats")
def stats(_: dict = Depends(require_government), d: Session = Depends(db)):
    rows = get_active_damages_query(d).all()
    history_rows = d.query(ComplaintHistory).all()
    return {
        "total": len(rows),
        "total_active": len(rows),
        "critical": sum(x.severity == "Critical" for x in rows),
        "high": sum(x.severity == "High" for x in rows),
        "medium": sum(x.severity == "Medium" for x in rows),
        "low": sum(x.severity == "Low" for x in rows),
        "pending": sum(x.status == "Pending" for x in rows),
        "pending_verification": sum(x.verification_status in {"Pending Verification", "Pending"} for x in rows),
        "verified": sum(x.verification_status == "Accepted" for x in rows),
        "in_progress": sum(x.status == "In Progress" for x in rows),
        "completed": sum(x.final_status == "Completed" for x in history_rows),
        "rejected": sum(x.final_status == "Rejected" for x in history_rows),
        "total_reports": sum((x.report_count or 1) for x in rows),
        "active_complaints": len(rows),
        "total_active": len(rows),
        "pending_verification": sum(x.verification_status in {"Pending Verification", "Pending"} for x in rows),
        "in_progress": sum(x.status == "In Progress" for x in rows),
        "completed": sum(x.final_status == "Completed" for x in history_rows),
        "rejected": sum(x.final_status == "Rejected" for x in history_rows),
    }
