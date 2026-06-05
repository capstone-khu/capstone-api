from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator, TypeAdapter, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors(v: str | list[str]) -> list[str]:
    if isinstance(v, str) and not v.startswith("["):
        return [origin.strip() for origin in v.split(",")]
    if isinstance(v, list):
        return v
    return TypeAdapter(list[str]).validate_python(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "capstone-api"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    MEDIA_ROOT: str = "media"

    CORS_ORIGINS: Annotated[list[str] | str, BeforeValidator(_parse_cors)] = []
    CORS_ORIGIN_REGEX: str | None = r"http://(localhost|127\.0\.0\.1):\d+"

    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "capstone"

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
