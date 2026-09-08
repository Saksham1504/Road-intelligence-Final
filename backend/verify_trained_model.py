from pathlib import Path

from ultralytics import YOLO

backend = Path(__file__).resolve().parent
model = YOLO(str(backend / "model" / "best.pt"))
data_yaml = backend / "datasets" / "road_damage" / "data.yaml"
images = sorted((backend / "datasets" / "road_damage" / "images" / "val").glob("*.jpg"))
print(f"images={len(images)}")
if not images:
    raise SystemExit("No validation images found")

metrics = model.val(
    data=str(data_yaml),
    imgsz=640,
    batch=16,
    conf=0.001,
    iou=0.6,
    plots=True,
    verbose=False,
)
print(f"names={model.names}")
print(f"precision={metrics.box.mp:.4f}")
print(f"recall={metrics.box.mr:.4f}")
print(f"map50={metrics.box.map50:.4f}")
print(f"map50_95={metrics.box.map:.4f}")

if metrics.box.map50 < 0.80 or metrics.box.mr < 0.80:
    raise SystemExit("Model quality is below the hackathon acceptance threshold")
