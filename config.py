from pydantic_settings import BaseSettings
import os

def default_db_file() -> str:
    if os.environ.get("DB_FILE"):
        return os.environ["DB_FILE"]
    if os.path.isdir("/data"):
        return "/data/toandaas_system.db"
    return "toandaas_system.db"

def default_backup_dir() -> str:
    if os.environ.get("DB_BACKUP_DIR"):
        return os.environ["DB_BACKUP_DIR"]
    if os.path.isdir("/data"):
        return "/data/backups"
    return "backups"

class Settings(BaseSettings):
    PROJECT_NAME: str = "TOAN AAS API Core"
    VERSION: str = "V1.0 (Phẳng & Nhanh)"
    
    # Database
    DB_FILE: str = default_db_file()
    DB_BACKUP_DIR: str = default_backup_dir()
    DB_STARTUP_BACKUP_ENABLED: bool = os.environ.get("DB_STARTUP_BACKUP_ENABLED", "true").lower() == "true"
    REQUIRE_PERSISTENT_DB: bool = os.environ.get("REQUIRE_PERSISTENT_DB", "false").lower() == "true"
    
    # PayOS
    PAYOS_CLIENT_ID: str = os.environ.get("PAYOS_CLIENT_ID", "")
    PAYOS_API_KEY: str = os.environ.get("PAYOS_API_KEY", "")
    PAYOS_CHECKSUM_KEY: str = os.environ.get("PAYOS_CHECKSUM_KEY", "")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
