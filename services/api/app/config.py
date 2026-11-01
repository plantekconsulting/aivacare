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
    chat_rate_per_minute = int(os.getenv("CHAT_RATE_PER_MINUTE", "30"))
    access_code = os.getenv("DEMO_ACCESS_CODE", "")
    # Cost guards for the shared demo (the Console spend limit is the hard ceiling).
    max_message_chars = int(os.getenv("MAX_MESSAGE_CHARS", "2000"))
    uploads_per_hour = int(os.getenv("UPLOADS_PER_HOUR", "10"))
    max_upload_pages = int(os.getenv("MAX_UPLOAD_PAGES", "10"))
    login_failures_per_15min = int(os.getenv("LOGIN_FAILURES_PER_15MIN", "10"))
    ai_daily_call_limit = int(os.getenv("AI_DAILY_CALL_LIMIT", "1000"))


settings = Settings()
