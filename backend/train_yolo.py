from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


DEFAULT_DATASET = Path(__file__).resolve().parent / "datasets" / "road_damage"
DEFAULT_MODEL = "yolov8n.pt"
DEFAULT_PROJECT = Path(__file__).resolve().parent / "runs" / "training"
CLASS_COUNT = 3


def build_data_yaml(dataset_root: Path) -> Path:
    dataset_root.mkdir(parents=True, exist_ok=True)
    (dataset_root / "images" / "train").mkdir(parents=True, exist_ok=True)
    (dataset_root / "images" / "val").mkdir(parents=True, exist_ok=True)
    (dataset_root / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (dataset_root / "labels" / "val").mkdir(parents=True, exist_ok=True)

    yaml_path = dataset_root / "data.yaml"
    yaml_content = """train: images/train
val: images/val
nc: 3
names: [\"pothole\", \"crack\", \"manhole\"]
"""
    yaml_path.write_text(yaml_content, encoding="utf-8")
    return yaml_path


def ensure_dataset(dataset_root: Path) -> Path:
    yaml_path = dataset_root / "data.yaml"
    if not yaml_path.exists():
        print(f"[INFO] No data.yaml found at {yaml_path}. Creating folder structure and template file.")
        return build_data_yaml(dataset_root)
    return yaml_path


def validate_labels(dataset_root: Path) -> None:
    """Fail early when malformed labels would make training unreliable."""
    for split in ("train", "val"):
        image_dir = dataset_root / "images" / split
        label_dir = dataset_root / "labels" / split
        images = [path for path in image_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        for image_path in images:
            label_path = label_dir / f"{image_path.stem}.txt"
            if not label_path.exists():
                raise ValueError(f"Missing label for {image_path.relative_to(dataset_root)}")
            for line_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), 1):
                values = line.split()
                if len(values) != 5:
                    raise ValueError(f"Invalid label at {label_path}:{line_number}: expected 5 values")
                try:
                    class_id = int(values[0])
                    coordinates = [float(value) for value in values[1:]]
                except ValueError as exc:
                    raise ValueError(f"Non-numeric label at {label_path}:{line_number}") from exc
                if not 0 <= class_id < CLASS_COUNT or any(value < 0 or value > 1 for value in coordinates):
                    raise ValueError(f"Out-of-range label at {label_path}:{line_number}")
                if coordinates[2] == 0 or coordinates[3] == 0:
                    raise ValueError(f"Zero-size box at {label_path}:{line_number}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a YOLO model for pothole, crack, and manhole detection.")
    parser.add_argument("--dataset", type=str, default=str(DEFAULT_DATASET), help="Path to the dataset root folder.")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Pretrained YOLO model to start from.")
    parser.add_argument("--epochs", type=int, default=80, help="Number of training epochs.")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size for training.")
    parser.add_argument("--batch", type=int, default=16, help="Batch size.")
    parser.add_argument("--project", type=str, default=str(DEFAULT_PROJECT), help="Directory for training outputs.")
    parser.add_argument("--name", type=str, default="road_damage_yolo", help="Name of the run.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset).resolve()
    data_yaml = ensure_dataset(dataset_root)

    if not data_yaml.exists():
        raise FileNotFoundError(f"Dataset config not found: {data_yaml}")

    train_images = dataset_root / "images" / "train"
    val_images = dataset_root / "images" / "val"
    if not train_images.exists() or not val_images.exists():
        print("[WARN] Dataset folders are still empty. Add labeled images to the following folders:")
        print(f"  - {train_images}")
        print(f"  - {val_images}")
        print(f"  - {dataset_root / 'labels' / 'train'}")
        print(f"  - {dataset_root / 'labels' / 'val'}")
        print(f"Then run this script again.")
        return

    validate_labels(dataset_root)

    model = YOLO(args.model)
    model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
        cache=True,
        pretrained=True,
        patience=35,
        val=True,
        plots=True,
        cos_lr=True,
        degrees=8.0,
        translate=0.12,
        scale=0.35,
        shear=3.0,
        perspective=0.0005,
        fliplr=0.5,
        mosaic=0.8,
        mixup=0.1,
        close_mosaic=10,
    )

    print("[INFO] Training completed.")
    print(f"[INFO] Best weights saved under: {Path(args.project).resolve() / args.name / 'weights' / 'best.pt'}")


if __name__ == "__main__":
    main()
