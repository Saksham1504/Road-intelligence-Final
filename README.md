# Road Intelligence — SIH MVP

This package uses the trained YOLO model supplied in the friend's ZIP and connects it to a FastAPI backend and React GIS dashboard.

## 1. Backend
Open terminal in `backend`:

Windows:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to verify the API.

## 2. Dashboard
Open a second terminal in `frontend`:
```
npm install
npm run dev
```
Open the Vite localhost URL.

## 3. Demo
Upload a road image in the dashboard and click **Run AI Detection**.
The backend loads the trained `road_damage` checkpoint from `road_damage/runs/detect/runs/detect/road_damage/weights/best.pt`, runs YOLO, stores detections in SQLite and places them on the map. Set `ROAD_DAMAGE_MODEL` before starting the backend to use a different checkpoint.

## Prototype severity
Severity is a transparent prototype rule using confidence + relative bounding-box area. It is NOT claimed as a clinically/engineering calibrated road-severity model.

## Classes
0 pothole
1 crack
2 manhole

## Important
The included `best.pt` is the trained model from the supplied ZIP. Do not retrain during the 1–2 hour prototype sprint unless inference fails.
