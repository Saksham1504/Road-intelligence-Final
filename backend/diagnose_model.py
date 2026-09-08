from pathlib import Path
from ultralytics import YOLO
from PIL import Image

BASE = Path(__file__).resolve().parent

MODEL_PATH = BASE / "model" / "best.pt"

# Use the exact image we have been testing
IMAGE_PATH = BASE / "uploads" / "616e04a1b2094f11aba048c39e896944.png"

model = YOLO(str(MODEL_PATH))

image = Image.open(IMAGE_PATH)

print("=" * 60)
print("MODEL DIAGNOSTIC")
print("=" * 60)

print("Image:", IMAGE_PATH.name)
print("Image size:", image.size)
print("Classes:", model.names)

print("\nRunning YOLO at extremely low confidence...")
print("This is ONLY a diagnostic test.")
print()

results = model.predict(
    source=str(IMAGE_PATH),
    imgsz=1280,
    conf=0.001,
    iou=0.45,
    max_det=100,
    verbose=False
)

result = results[0]

print("TOTAL RAW DETECTIONS:", len(result.boxes))
print()

for i, box in enumerate(result.boxes):

    cls_id = int(box.cls[0].item())
    confidence = float(box.conf[0].item())

    x1, y1, x2, y2 = box.xyxy[0].tolist()

    class_name = model.names[cls_id]

    print(
        f"{i+1:02d}. "
        f"{class_name:<10} "
        f"confidence={confidence:.4f} "
        f"({confidence*100:.2f}%) "
        f"box=({int(x1)}, {int(y1)}, {int(x2)}, {int(y2)})"
    )

print()
print("=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)