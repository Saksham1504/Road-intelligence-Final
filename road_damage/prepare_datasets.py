import os
import random
import shutil

# ============================================================
# CONFIGURATION
# ============================================================

# Original dataset
SOURCE_IMAGES = "data/images"
SOURCE_LABELS = "data/labels-YOLO"

# Prepared YOLO dataset
OUTPUT = "road_damage"

# Dataset split ratios
TRAIN_RATIO = 0.70
VAL_RATIO = 0.20
TEST_RATIO = 0.10

# YOLO class names
CLASS_NAMES = {
    0: "pothole",
    1: "crack",
    2: "manhole"
}

# Reproducibility
random.seed(42)


# ============================================================
# CHECK SOURCE FOLDERS
# ============================================================

if not os.path.exists(SOURCE_IMAGES):
    raise FileNotFoundError(
        f"Images folder not found: {os.path.abspath(SOURCE_IMAGES)}"
    )

if not os.path.exists(SOURCE_LABELS):
    raise FileNotFoundError(
        f"Labels folder not found: {os.path.abspath(SOURCE_LABELS)}"
    )


# ============================================================
# CREATE OUTPUT FOLDERS
# ============================================================

for split in ["train", "val", "test"]:

    os.makedirs(
        os.path.join(OUTPUT, "images", split),
        exist_ok=True
    )

    os.makedirs(
        os.path.join(OUTPUT, "labels", split),
        exist_ok=True
    )


# ============================================================
# FIND IMAGES
# ============================================================

images = [
    f
    for f in os.listdir(SOURCE_IMAGES)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]

if len(images) == 0:
    raise RuntimeError(
        f"No images found in {os.path.abspath(SOURCE_IMAGES)}"
    )

# Shuffle images
random.shuffle(images)

total_images = len(images)


# ============================================================
# CALCULATE SPLITS
# ============================================================

train_end = int(total_images * TRAIN_RATIO)

val_end = train_end + int(total_images * VAL_RATIO)

train_images = images[:train_end]

val_images = images[train_end:val_end]

test_images = images[val_end:]


splits = {
    "train": train_images,
    "val": val_images,
    "test": test_images
}


# ============================================================
# COPY IMAGES AND LABELS
# ============================================================

missing_labels = []

copied_images = 0
copied_labels = 0


for split, files in splits.items():

    print(f"\nPreparing {split} dataset...")

    for image_file in files:

        # ----------------------------------------------------
        # Image paths
        # ----------------------------------------------------

        image_src = os.path.join(
            SOURCE_IMAGES,
            image_file
        )

        image_dst = os.path.join(
            OUTPUT,
            "images",
            split,
            image_file
        )

        # ----------------------------------------------------
        # Label paths
        # ----------------------------------------------------

        label_file = (
            os.path.splitext(image_file)[0]
            + ".txt"
        )

        label_src = os.path.join(
            SOURCE_LABELS,
            label_file
        )

        label_dst = os.path.join(
            OUTPUT,
            "labels",
            split,
            label_file
        )

        # ----------------------------------------------------
        # Copy image
        # ----------------------------------------------------

        shutil.copy2(
            image_src,
            image_dst
        )

        copied_images += 1

        # ----------------------------------------------------
        # Copy label
        # ----------------------------------------------------

        if os.path.exists(label_src):

            shutil.copy2(
                label_src,
                label_dst
            )

            copied_labels += 1

        else:

            missing_labels.append(image_file)


# ============================================================
# CREATE data.yaml
# ============================================================

dataset_path = os.path.abspath(OUTPUT)

# Convert Windows backslashes to forward slashes
dataset_path = dataset_path.replace("\\", "/")

yaml_content = f"""path: {dataset_path}

train: images/train
val: images/val
test: images/test

names:
"""

for class_id, class_name in CLASS_NAMES.items():

    yaml_content += (
        f"  {class_id}: {class_name}\n"
    )


yaml_path = os.path.join(
    OUTPUT,
    "data.yaml"
)


with open(
    yaml_path,
    "w",
    encoding="utf-8"
) as file:

    file.write(yaml_content)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 50)

print("DATASET PREPARATION COMPLETE!")

print("=" * 50)

print(f"Total images : {total_images}")

print(f"Training     : {len(train_images)}")

print(f"Validation   : {len(val_images)}")

print(f"Testing      : {len(test_images)}")

print(f"Images copied: {copied_images}")

print(f"Labels copied: {copied_labels}")

print(
    f"Missing labels: {len(missing_labels)}"
)

print(
    f"\ndata.yaml created at:\n"
    f"{os.path.abspath(yaml_path)}"
)


# ============================================================
# MISSING LABEL WARNING
# ============================================================

if missing_labels:

    print("\nWARNING!")
    print(
        f"{len(missing_labels)} images do not have "
        "corresponding YOLO label files."
    )

    print("\nFirst 10 missing labels:")

    for filename in missing_labels[:10]:

        print(" -", filename)

else:

    print(
        "\nAll images have corresponding YOLO labels."
    )


print("\nDataset structure:")

print(
    f"""
{OUTPUT}/
├── data.yaml
├── images/
│   ├── train/
│   ├── val/
│   └── test/
└── labels/
    ├── train/
    ├── val/
    └── test/
"""
)

