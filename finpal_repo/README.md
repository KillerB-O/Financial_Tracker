# FinPal - Ready-to-run Scaffold (Demo)
This repository is a scaffold for the FinPal project (FastAPI backend + Flutter mobile app + on-device ML).

Contents:
- backend/: FastAPI minimal app
- mobile_app/: Flutter scaffold (placeholder files)
- ml_models/: Place ML models here
- docs/: Project docs and notes

## How to run backend locally
```
cd /mnt/data/finpal_repo/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Visit http://127.0.0.1:8000/health

## Flutter app
The `mobile_app` folder contains placeholder Dart files. To run:
- Install Flutter SDK
- From the mobile_app folder run `flutter pub get` then `flutter run`

## Next steps (suggested)
- Implement full SMS parsing and tests
- Implement on-device models (TFLite) and integrate with Flutter
- Build the full FastAPI routers for community/peer stats if opting for backend
