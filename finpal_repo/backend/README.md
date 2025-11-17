# FinPal Backend (Minimal)
This is a minimal FastAPI scaffold for the FinPal project. It exposes a health endpoint.

Run locally:
```
cd backend
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```
