from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./data/app.db"
    
    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS - Support for remote access
    CORS_ORIGINS: List[str] = [
        "http://localhost:3721",      # Local development
        "http://127.0.0.1:3721",      # Localhost alternative
        "http://192.168.1.100:3721"   # Default server IP (change as needed)
    ]
    
    # Server configuration for deployment
    SERVER_IP: str = "localhost"
    FRONTEND_PORT: str = "3721"
    
    # Admin user (created on first run)
    FIRST_ADMIN_USERNAME: Optional[str] = None
    FIRST_ADMIN_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return self.DATABASE_URL

    @property
    def dynamic_cors_origins(self) -> List[str]:
        """Generate CORS origins dynamically based on SERVER_IP."""
        origins = [
            "http://localhost:3721",
            "http://127.0.0.1:3721"
        ]
        
        # Add server IP if it's not localhost
        if self.SERVER_IP != "localhost" and self.SERVER_IP != "127.0.0.1":
            origins.append(f"http://{self.SERVER_IP}:{self.FRONTEND_PORT}")
        
        # Include any additional origins from CORS_ORIGINS
        for origin in self.CORS_ORIGINS:
            if origin not in origins:
                origins.append(origin)
        
        return origins


@lru_cache()
def get_settings() -> Settings:
    return Settings() 
