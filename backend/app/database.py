from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.base import Base
from app.core.config import settings

engine = create_engine(
    settings.database_url
)

SessionLocal=sessionmaker(
    autoflush=False,
    autocommit=False,
    bind=engine
)

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()