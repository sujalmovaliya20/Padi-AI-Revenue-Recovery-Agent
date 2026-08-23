"""SQLAlchemy engine & session factory."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

connect_args = {}
if "postgresql" in settings.DATABASE_URL:
    connect_args["connect_timeout"] = 2

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def init_db():
    """Create database tables if they do not already exist."""
    try:
        import app.models  # noqa: F401 - ensure models are registered
        with engine.connect() as conn:
            Base.metadata.create_all(bind=conn)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning("Database unavailable, skipping table creation on startup: %s", e)


def get_db():
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
