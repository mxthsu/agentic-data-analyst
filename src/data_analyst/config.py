from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, StringConstraints, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_path: Path = Path("data/anexo_desafio_1.db")

    google_api_key: SecretStr
    gemini_model: NonEmptyStr = "gemini-3.5-flash-lite"
    gemini_requests_per_minute: int = Field(default=6, ge=1, le=60)
    gemini_max_burst_requests: int = Field(default=5, ge=1, le=10)
    gemini_request_timeout_seconds: float = Field(default=30.0, ge=5, le=120)
    gemini_max_output_tokens: int = Field(default=1024, ge=128, le=4096)

    @field_validator("google_api_key")
    @classmethod
    def validate_api_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("GOOGLE_API_KEY não pode estar vazia.")
        return value
