from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


DATASET_ROOT = Path(__file__).resolve().parent / "datasets" / "road_damage"
TRAIN_IMAGES = DATASET_ROOT / "images" / "train"
VAL_IMAGES = DATASET_ROOT / "images" / "val"
TRAIN_LABELS = DATASET_ROOT / "labels" / "train"
VAL_LABELS = DATASET_ROOT / "labels" / "val"

CLASS_MAP = {
    "pothole": 0,
    "crack": 1,
    "manhole": 2,
}

random.seed(7)


def road_base_color():
    return random.choice([(96, 98, 102), (108, 110, 114), (86, 88, 92), (76, 79, 82)])


def add_road_texture(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    base = road_base_color()
    draw.rectangle((0, 0, width, height), fill=base)

    for y in range(0, height, 32):
        draw.rectangle((0, y, width, y + 16), fill=(base[0] + 12, base[1] + 12, base[2] + 12))

    for i in range(200):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = x1 + random.randint(30, 100)
        y2 = y1 + random.randint(5, 18)
        draw.line((x1, y1, x2, y2), fill=(base[0] + 14, base[1] + 14, base[2] + 14), width=2)

    for i in range(500):
        x = random.randint(0, width)
        y = random.randint(0, height)
        r = random.randint(1, 3)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(base[0] - 10, base[1] - 10, base[2] - 12))


def add_shadows_and_lines(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    for _ in range(8):
        x0 = random.randint(0, img.width)
        y0 = random.randint(0, img.height)
        x1 = x0 + random.randint(100, 350)
        y1 = y0 + random.randint(-60, 70)
        draw.line((x0, y0, x1, y1), fill=(0, 0, 0, 40), width=random.randint(2, 8))


def make_pothole(draw: ImageDraw.ImageDraw, x: int, y: int, size: int):
    pad = size // 8
    bbox = (x - size // 2, y - size // 2, x + size // 2, y + size // 2)
    draw.ellipse(bbox, fill=(18, 18, 20), outline=(44, 44, 48), width=max(2, size // 10))
    draw.ellipse((x - size // 2 + pad, y - size // 2 + pad, x + size // 2 - pad, y + size // 2 - pad), fill=(10, 10, 12))
    for i in range(6):
        angle = (i / 6) * 3.14159 * 2
        r = size * 0.35
        px = x + int(r * __import__('math').cos(angle))
        py = y + int(r * __import__('math').sin(angle))
        draw.line((x, y, px, py), fill=(30, 30, 34), width=2)
    return bbox


def make_crack(draw: ImageDraw.ImageDraw, x: int, y: int, size: int):
    points = []
    for i in range(9):
        t = i / 8
        px = x + int((t - 0.5) * size)
        py = y + int((random.random() - 0.5) * size * 1.2)
        points.append((px, py))
    draw.line(points, fill=(220, 220, 220), width=max(2, size // 18))
    for px, py in points:
        draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=(245, 245, 245))
    return (x - size // 2, y - size // 2, x + size // 2, y + size // 2)


def make_manhole(draw: ImageDraw.ImageDraw, x: int, y: int, size: int):
    bbox = (x - size // 2, y - size // 2, x + size // 2, y + size // 2)
    draw.ellipse(bbox, fill=(36, 37, 40), outline=(170, 170, 170), width=max(2, size // 16))
    draw.ellipse((x - size // 3, y - size // 3, x + size // 3, y + size // 3), fill=(20, 20, 22))
    draw.line((x - size // 3, y, x + size // 3, y), fill=(200, 200, 200), width=max(2, size // 18))
    draw.line((x, y - size // 3, x, y + size // 3), fill=(200, 200, 200), width=max(2, size // 18))
    return bbox


def add_damage(img: Image.Image, damage_name: str):
    draw = ImageDraw.Draw(img)
    x = random.randint(80, img.width - 80)
    y = random.randint(80, img.height - 80)
    size = random.randint(52, 150)
    if damage_name == "pothole":
        bbox = make_pothole(draw, x, y, size)
    elif damage_name == "crack":
        bbox = make_crack(draw, x, y, size)
    else:
        bbox = make_manhole(draw, x, y, size)
    x1, y1, x2, y2 = bbox
    x_center = ((x1 + x2) / 2) / img.width
    y_center = ((y1 + y2) / 2) / img.height
    box_w = (x2 - x1) / img.width
    box_h = (y2 - y1) / img.height
    return f"{CLASS_MAP[damage_name]} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}"


def generate_sample(split: str, index: int):
    width, height = 640, 640
    img = Image.new("RGB", (width, height), color=(80, 80, 82))
    draw = ImageDraw.Draw(img)
    add_road_texture(draw, width, height)
    add_shadows_and_lines(img)

    labels = []
    damage_types = ["pothole", "crack", "manhole"]
    count = random.randint(1, 3)
    chosen = random.sample(damage_types, k=count)
    for damage_name in chosen:
        labels.append(add_damage(img, damage_name))

    folder = TRAIN_IMAGES if split == "train" else VAL_IMAGES
    label_folder = TRAIN_LABELS if split == "train" else VAL_LABELS
    folder.mkdir(parents=True, exist_ok=True)
    label_folder.mkdir(parents=True, exist_ok=True)

    file_name = f"road_damage_{split}_{index}.jpg"
    img = img.filter(ImageFilter.GaussianBlur(radius=0.2))
    img.save(folder / file_name)
    (label_folder / f"{Path(file_name).stem}.txt").write_text("\n".join(labels) + "\n", encoding="utf-8")


def main():
    for split, count in [("train", 120), ("val", 30)]:
        for i in range(count):
            generate_sample(split, i)
    print(f"[OK] Generated richer synthetic road-damage dataset in {DATASET_ROOT}")
    print("  - train images: 120")
    print("  - val images: 30")


if __name__ == "__main__":
    main()
