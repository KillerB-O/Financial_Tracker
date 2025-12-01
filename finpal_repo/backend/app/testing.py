from .db.session import SessionLocal  # or however you create sessions
from .db.models.recommendation import Recommendation
from .core.config import SQLALCHEMY_DATABASE_URL

db = SessionLocal()
recs = db.query(Recommendation).all()
if recs:
    print(recs)
else:
    print("NOOOOOO!")
db.close()