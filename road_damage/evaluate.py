from pathlib import Path
from ultralytics import YOLO


def main():
    base_dir = Path(__file__).resolve().parent
    data_yaml = base_dir / "road_damage" / "data.yaml"
    test_source = base_dir / "road_damage" / "images" / "test"

    # Path to existing trained weights
    weights_path = (
        base_dir
        / "runs"
        / "detect"
        / "runs"
        / "detect"
        / "road_damage"
        / "weights"
        / "best.pt"
    )

    print(f"Loading trained model from: {weights_path}")
    model = YOLO(str(weights_path))

    # 1. Validation
    print("\n--- Running Validation ---")
    metrics = model.val(data=str(data_yaml), device=0)

    print("\n--- Model Performance ---")
    print(f"mAP50:    {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")

    # 2. Test Predictions
    print("\n--- Generating Test Predictions ---")
    model.predict(source=str(test_source), conf=0.20, save=True, device=0)

    print("\nEvaluation finished! Outputs saved in 'runs/detect/predict'.")


if __name__ == "__main__":
    main()