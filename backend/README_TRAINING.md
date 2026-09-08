# Road damage YOLO training guide

This project can be trained to detect potholes, cracks, and manholes using Ultralytics YOLO.

## 1) Prepare dataset
Create a dataset structure like this:

road_damage/
  data.yaml
  images/
    train/
    val/
  labels/
    train/
    val/

The example file `data.yaml` should look like this:

```yaml
train: images/train
val: images/val
nc: 3
names: ["pothole", "crack", "manhole"]
```

Each annotation file should be in YOLO txt format:

```text
0 0.512 0.481 0.234 0.185
```

The class numbers correspond to:
- 0 = pothole
- 1 = crack
- 2 = manhole

## 2) Put images into the dataset
- Add labeled training images to `datasets/road_damage/images/train`
- Add labeled validation images to `datasets/road_damage/images/val`
- Add matching `.txt` annotation files to `datasets/road_damage/labels/train` and `labels/val`

## 3) Run training
From the backend folder:

```powershell
.\.venv\Scripts\python.exe train_yolo.py --dataset datasets/road_damage --epochs 80 --imgsz 640 --batch 16
```

This trains a YOLO model and writes the best checkpoint to:

`runs/road_damage_yolo/weights/best.pt`

## 4) Use the trained model in the app
After training, update the file path in `backend/main.py` or copy the trained weights into:

```text
backend/model/best.pt
```

## 5) Notes
- Keep the lighting and camera angle consistent.
- Include close-up road damage images with clear edges.
- Label potholes, cracks, and manholes consistently.
- If detection quality is weak, add more photos and increase the dataset diversity.
