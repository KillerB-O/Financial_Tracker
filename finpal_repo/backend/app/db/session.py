# backend/app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import SQLALCHEMY_DATABASE_URL

engine=create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={} if not SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {"check_same_thread": False},
    pool_pre_ping=True,
    echo=False, #debugging =false
    future=True  #SQLAlchemy 2.0
    )

SessionLocal=sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)

def get_db():                   #core of SQLAlchemy transaction management 
    db=SessionLocal()             # every request that interacts with the database gets: 
    try:                                           #fresh database session,automatic COMMIT if everything succeeds,automatic ROLLBACK if something fails
        yield db                                   #yield send database session "db" to my API endpoints
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()      #the session is always closed no matter what happens(succeed/fail)