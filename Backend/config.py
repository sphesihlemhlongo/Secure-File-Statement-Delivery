from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    # Supabase API
    supabase_url: str = Field(..., validation_alias="SUPABASE_URL")
    supabase_key: str = Field(..., validation_alias="SUPABASE_KEY")

    # Security
    secret_key: str = Field(..., validation_alias="SECRET_KEY")
    server_selector_secret: str = Field(..., validation_alias="SERVER_SELECTOR_SECRET")
    download_secret: str = Field(..., validation_alias="DOWNLOAD_SECRET")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    download_token_ttl_seconds: int = Field(default=180, validation_alias="DOWNLOAD_TOKEN_TTL_SECONDS")

    # Storage
    # On Vercel, we should use /tmp, but we handle this in main.py dynamically now.
    # This setting is kept for backward compatibility or local dev if needed, 
    # though main.py now prefers tempfile.gettempdir()
    upload_dir: str = Field(default="/tmp", validation_alias="UPLOAD_DIR")

    # AI
    gemini_api_key: str = Field(..., validation_alias="Gemini")


# We use a try-except block to catch validation errors at import time if needed,
# but letting it fail is also acceptable for "Validates presence of required env vars".
try:
    settings = Settings()
except Exception as e:
    print(f"Configuration Error: {e}")
    # In production, you might want to exit here, but for now we let it crash naturally or handle it in main.
    raise

