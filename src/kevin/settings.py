from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Kevin API"
    debug: bool = False
    database_url: str = "postgresql+psycopg://kevin:kevin@localhost:5432/kevin"
    secret_key: str  # Required — no default. App will fail to start without it.
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:8081",
        "http://localhost:19006",
        "http://localhost:3000",
    ]

    model_config = {"env_file": ".env", "env_prefix": "KEVIN_"}

    @model_validator(mode="after")
    def fix_database_driver(self) -> "Settings":
        # Render provides postgresql:// but we need postgresql+psycopg://
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
        return self


settings = Settings()
