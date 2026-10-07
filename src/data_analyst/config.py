from pathlib import Path
from typing import Annotated

from pydantic import SecretStr, StringConstraints, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_path: Path = Path("data/anexo_desafio_1.db")
    openrouter_api_key: SecretStr
    openrouter_model: NonEmptyStr

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("OPENROUTER_API_KEY não pode estar vazia.")
        return value
