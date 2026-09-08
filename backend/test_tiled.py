from ultralytics import YOLO
from pathlib import Path
from PIL import Image

MODEL = YOLO("model/best.pt")

IMAGE = "uploads/616e04a1b2094f11aba048c39e896944.png"

img = Image.open(IMAGE)
width, height = img.size

print("Image size:", width, height)

tile_w = width // 2
tile_h = height // 2

detections = []

for row in range(2):
    for col in range(2):
        left = col * tile_w
        top = row * tile_h
        right = width if col == 1 else (col + 1) * tile_w
        bottom = height if row == 1 else (row + 1) * tile_h

        tile = img.crop((left, top, right, bottom))

        result = MODEL.predict(
            source=tile,
            conf=0.05,
            iou=0.45,
            imgsz=1280,
            verbose=False
        )[0]

        print(f"\nTile {row},{col}: {len(result.boxes)} detections")

        for box in result.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])

            print(
                f"  {MODEL.names[cls]} "
                f"confidence={conf:.3f}"
            )

            detections.append((MODEL.names[cls], conf))

print("\nTOTAL DETECTIONS:", len(detections))