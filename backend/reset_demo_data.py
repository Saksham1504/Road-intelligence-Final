import shutil
from sqlalchemy import text

from main import engine, BASE, UPLOAD_DIR


def reset_demo_data():
    with engine.begin() as conn:
        tables = ["complaint_history_detections", "complaint_detections", "complaint_reports", "complaint_history", "damages"]
        for table in tables:
            try:
                conn.execute(text(f"DELETE FROM {table}"))
            except Exception:
                pass

        try:
            conn.execute(text("DELETE FROM sqlite_sequence WHERE name IN ('damages', 'complaint_history', 'complaint_history_detections', 'complaint_detections', 'complaint_reports')"))
        except Exception:
            pass

    # Every file in uploads is generated complaint evidence. Keep the folder
    # itself because FastAPI mounts it as a static directory.
    for item in UPLOAD_DIR.iterdir():
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink()
        except OSError:
            pass

    print("Demo complaint data and complaint images have been reset.")
    print("Model files, datasets, and schema were preserved.")
    print("Database counts: 0 active complaints, 0 history entries, 0 reports.")


if __name__ == "__main__":
    reset_demo_data()
