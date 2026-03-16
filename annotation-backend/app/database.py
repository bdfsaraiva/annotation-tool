from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import get_settings
from .models import Base

settings = get_settings()

database_url = settings.SQLALCHEMY_DATABASE_URL

# Only SQLite uses check_same_thread
connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    database_url,
    connect_args=connect_args
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 
