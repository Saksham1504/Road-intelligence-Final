from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    dataset_root = Path(__file__).resolve().parent / "datasets" / "road_damage"
    config = dataset_root / "data.yaml"

    print(f"[INFO] Dataset root: {dataset_root}")
    if not config.exists():
        print("[ERROR] Missing data.yaml. Run train_yolo.py first or create the dataset structure.")
        return 1

    train_images = sorted((dataset_root / "images" / "train").glob("*"))
    val_images = sorted((dataset_root / "images" / "val").glob("*"))
    train_labels = sorted((dataset_root / "labels" / "train").glob("*"))
    val_labels = sorted((dataset_root / "labels" / "val").glob("*"))

    image_files = [p for p in train_images + val_images if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
    label_files = [p for p in train_labels + val_labels if p.suffix.lower() == ".txt"]

    print(f"[INFO] Train images: {len(train_images)}")
    print(f"[INFO] Validation images: {len(val_images)}")
    print(f"[INFO] Train labels: {len(train_labels)}")
    print(f"[INFO] Validation labels: {len(val_labels)}")
    print(f"[INFO] Total image files: {len(image_files)}")
    print(f"[INFO] Total label files: {len(label_files)}")

    missing_labels = []
    for image in image_files:
        label = (dataset_root / "labels" / ("train" if str(image.parent).endswith("train") else "val")) / (image.stem + ".txt")
        if not label.exists():
            missing_labels.append(str(label.relative_to(dataset_root)))

    if missing_labels:
        print("[WARN] Missing matching labels for some images:")
        for item in missing_labels[:10]:
            print(f"  - {item}")
        if len(missing_labels) > 10:
            print(f"  ... and {len(missing_labels) - 10} more")
        return 2

    print("[OK] Dataset structure looks consistent for YOLO training.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
