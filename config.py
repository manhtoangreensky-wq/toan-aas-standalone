from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "TOAN AAS API Core"
    VERSION: str = "V1.0 (Phẳng & Nhanh)"
    
    # Database
    DB_FILE: str = os.environ.get("DB_FILE", "toandaas_system.db")
    
    # PayOS
    PAYOS_CLIENT_ID: str = os.environ.get("PAYOS_CLIENT_ID", "")
    PAYOS_API_KEY: str = os.environ.get("PAYOS_API_KEY", "")
    PAYOS_CHECKSUM_KEY: str = os.environ.get("PAYOS_CHECKSUM_KEY", "")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()