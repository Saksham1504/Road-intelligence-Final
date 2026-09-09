from pathlib import Path
from ultralytics import YOLO


def main():
    base_dir = Path(__file__).resolve().parent
    data_yaml = base_dir / "road_damage" / "data.yaml"

    model = YOLO("yolo26n.pt")

    model.train(
        data=str(data_yaml),
        epochs=120,
        imgsz=800,
        batch=8,
        device=0,
        patience=25,
        workers=2,
        project="runs",
        name="road_damage",
        exist_ok=True,
        save=True,
        hsv_v=0.4,
        hsv_s=0.5,
        degrees=10.0,
    )


if __name__ == "__main__":
    main()