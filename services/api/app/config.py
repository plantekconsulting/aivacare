import os
from pathlib import Path

APP_DIR = Path(__file__).parent


class Settings:
    database_url = os.getenv("DATABASE_URL", "postgresql://aivacare:aivacare@localhost:5432/aivacare")
    fhir_base_url = os.getenv("FHIR_BASE_URL", "http://localhost:8090/fhir").rstrip("/")
    model_main = os.getenv("MODEL_MAIN", "claude-opus-5-5")
    model_fast = os.getenv("MODEL_FAST", "claude-haiku-5-5")
    jwt_secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
    cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
    chat_rate_per_minute = int(os.getenv("CHAT_RATE_PER_MINUTE", "12"))


settings = Settings()
