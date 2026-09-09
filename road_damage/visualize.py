import glob
import cv2
import matplotlib.pyplot as plt
from pathlib import Path


def main():
    base_dir = Path(__file__).resolve().parent
    # Path where model.predict() saved the annotated test images
    predict_dir = base_dir / "runs" / "detect" / "predict"

    # Find all PNG/JPG output images
    image_paths = glob.glob(str(predict_dir / "*.jpg")) + glob.glob(
        str(predict_dir / "*.png")
    )

    if not image_paths:
        print(f"No prediction images found in {predict_dir}")
        return

    # Display the first 4 predicted images in a grid
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.ravel()

    for idx, img_path in enumerate(image_paths[:4]):
        img = cv2.imread(img_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        axes[idx].imshow(img_rgb)
        axes[idx].set_title(Path(img_path).name)
        axes[idx].axis("off")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()