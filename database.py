# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# If DATABASE_URL contains "neon" or "sslmode", it's a cloud DB
# Otherwise it's local — no SSL needed
if "sslmode=require" in settings.database_url or "neon.tech" in settings.database_url:
    engine = create_engine(
        settings.database_url,
        connect_args={"sslmode": "require"}
    )
else:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()