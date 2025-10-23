from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database settings
    PGHOST: str = "127.0.0.1"
    PGPORT: int = 5432
    PGUSER: str = "postgres"
    PGPASSWORD: str = ""
    PGDATABASE: str = "postgres"
    
    # MinIO settings
    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "MINIO_ACCESS"
    MINIO_SECRET_KEY: str = "MINIO_SECRET"
    MINIO_SECURE: bool = False
    MINIO_MEDIA_BUCKET: str = "orato-media"
    
    # Video processing settings
    MAX_DURATION_SECONDS: int = 300  # 5 minutes
    SUPPORTED_LANGUAGE: str = "en"
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "OratoAI"
    
    class Config:
        """Pydantic config for environment variable loading"""
        env_file = "config.env"  # Load from config.env file
        case_sensitive = True  # Case sensitive environment variables

# Create global settings instance
settings = Settings()

# Debug: Print loaded settings (remove in production)
print(f"🔧 Database config: {settings.PGHOST}:{settings.PGPORT}/{settings.PGDATABASE}")
print(f"🔧 MinIO config: {settings.MINIO_ENDPOINT}")
print(f"🔧 Password set: {'Yes' if settings.PGPASSWORD else 'No'}")
