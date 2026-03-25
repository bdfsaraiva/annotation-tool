"""
Database engine and session factory for the LACE backend.

Creates a single SQLAlchemy ``engine`` bound to the configured
``DATABASE_URL``.  ``SessionLocal`` is a session factory used throughout
the application, and ``get_db`` is a FastAPI dependency that yields a
request-scoped database session.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

from .config import get_settings
from .models import Base

settings = get_settings()

database_url = settings.SQLALCHEMY_DATABASE_URL

# SQLite requires check_same_thread=False because FastAPI can run handlers
# on different threads.  Other databases do not need this argument.
connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    database_url,
    connect_args=connect_args
)

# autocommit=False and autoflush=False are the recommended defaults for
# web applications, where transactions are committed explicitly.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """
    FastAPI dependency that provides a database session for a single request.

    Opens a new ``SessionLocal`` session, yields it to the route handler, and
    closes it in the ``finally`` block so the connection is always returned to
    the pool even if an exception is raised.

    Yields:
        Session: An active SQLAlchemy ORM session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
