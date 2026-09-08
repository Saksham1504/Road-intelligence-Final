from pathlib import Path
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import math
import uuid

import cv2
import requests
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from ultralytics import YOLO

BASE = Path(__file__).resolve().parent
MODEL_PATH = BASE / "model" / "best.pt"
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
engine = create_engine(
    "sqlite:///" + str(BASE / "road_intelligence.db"),
    connect_args={"check_same_thread": False},
)
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
    image_url = Column(String)
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    latest_reported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    report_count = Column(Integer, default=1, nullable=False)


Base.metadata.create_all(engine)


def seed_demo_complaints():
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


# Small migration for an existing SQLite database created by the original prototype.
with engine.begin() as conn:
    columns = {c["name"] for c in inspect(engine).get_columns("damages")}
    if "address" not in columns:
        conn.execute(text("ALTER TABLE damages ADD COLUMN address VARCHAR"))
    if "latest_reported_at" not in columns:
        conn.execute(text("ALTER TABLE damages ADD COLUMN latest_reported_at DATETIME"))
        conn.execute(text("UPDATE damages SET latest_reported_at = detected_at WHERE latest_reported_at IS NULL"))
    if "report_count" not in columns:
        conn.execute(text("ALTER TABLE damages ADD COLUMN report_count INTEGER NOT NULL DEFAULT 1"))

seed_demo_complaints()

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


def find_existing_complaint(d: Session, item: dict, latitude: float, longitude: float, now: datetime):
    window_start = now.replace(tzinfo=None) - timedelta(hours=DUPLICATE_WINDOW_HOURS)
    candidates = d.query(Damage).filter(
        Damage.damage_type == item["damage_type"],
        Damage.latest_reported_at >= window_start,
    ).all()
    return next(
        (
            row for row in candidates
            if distance_meters(latitude, longitude, row.latitude, row.longitude) <= DUPLICATE_RADIUS_METERS
        ),
        None,
    )


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
    image_url = f"/uploads/{annotated_name}"
    address = address_override.strip() if address_override and address_override.strip() else reverse_geocode(latitude, longitude)

    # Every detected object becomes a complaint record linked to the same report image/location.
    now = datetime.now(timezone.utc)
    created_ids = []
    linked_ids = []
    updated_existing_ids = set()
    processed_detections = []
    for item in detections:
        existing = find_existing_complaint(d, item, latitude, longitude, now)
        if existing is not None and existing.id not in created_ids:
            if existing.id not in updated_existing_ids:
                existing.report_count = (existing.report_count or 1) + 1
                existing.latest_reported_at = now
                existing.confidence = max(existing.confidence, item["confidence"])
                existing.image_url = image_url
                updated_existing_ids.add(existing.id)
                linked_ids.append(existing.id)
            item.update({"complaint_id": existing.id, "linked": True, "report_count": existing.report_count})
        else:
            row = Damage(
                damage_type=item["damage_type"],
                confidence=item["confidence"],
                severity=item["severity"],
                latitude=latitude,
                longitude=longitude,
                address=address,
                status="Pending",
                image_url=image_url,
                detected_at=now,
                latest_reported_at=now,
                report_count=1,
            )
            d.add(row)
            d.flush()
            created_ids.append(row.id)
            item.update({"complaint_id": row.id, "linked": False, "report_count": 1})
        processed_detections.append(item)
    d.commit()

    complaint_ids = list(dict.fromkeys(created_ids + linked_ids))
    complaint_id = complaint_ids[0] if complaint_ids else None
    return {
        "count": len(detections),
        "complaint_id": complaint_id,
        "complaint_ids": complaint_ids,
        "created_complaint_ids": created_ids,
        "linked_complaint_ids": linked_ids,
        "detections": processed_detections,
        "image_url": image_url,
        "latitude": latitude,
        "longitude": longitude,
        "location_accuracy_m": location_accuracy_m,
        "address": address,
        "complaint_registered": len(complaint_ids) > 0,
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
    return d.query(Damage).order_by(Damage.id.desc()).all()


@app.get("/api/dashboard/stats")
def stats(_: dict = Depends(require_government), d: Session = Depends(db)):
    rows = d.query(Damage).all()
    return {
        "total": len(rows),
        "critical": sum(x.severity == "Critical" for x in rows),
        "high": sum(x.severity == "High" for x in rows),
        "medium": sum(x.severity == "Medium" for x in rows),
        "low": sum(x.severity == "Low" for x in rows),
        "pending": sum(x.status == "Pending" for x in rows),
        "verified": sum(x.status == "Verified" for x in rows),
        "in_progress": sum(x.status == "In Progress" for x in rows),
        "repaired": sum(x.status == "Repaired" for x in rows),
    }


@app.patch("/api/damages/{damage_id}/status")
def update_status(
    damage_id: int,
    status: str,
    _: dict = Depends(require_government),
    d: Session = Depends(db),
):
    allowed = {"Pending", "Verified", "Rejected", "Assigned", "In Progress", "Repaired"}
    if status not in allowed:
        raise HTTPException(400, "Invalid status")
    row = d.query(Damage).filter(Damage.id == damage_id).first()
    if not row:
        raise HTTPException(404, "Damage not found")
    row.status = status
    d.commit()
    d.refresh(row)
    return row
