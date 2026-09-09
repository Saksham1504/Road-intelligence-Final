from ultralytics import YOLO

model = YOLO("runs/detect/runs/detect/road_damage/weights/best.pt")

model.predict(
    source="road_damage/images/test",
    conf=0.25,
    save=True
)

print("Prediction completed.")