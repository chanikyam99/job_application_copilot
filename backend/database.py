from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./job_copilot.db")

# connect_args={"check_same_thread": False} is SQLite-specific.
# SQLite normally refuses access from multiple threads.
# FastAPI uses a thread pool, so without this flag you get:
#   "SQLite objects created in a thread can only be used in that same thread"
# When you switch to Postgres, remove it — Postgres handles concurrency natively.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class for all ORM models.
# Every model class inherits from Base so SQLAlchemy knows the table exists.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency: opens a DB session for each request, closes it after.
    Used as: db: Session = Depends(get_db) in every endpoint function.
    The try/finally ensures the session closes even if the endpoint raises.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()