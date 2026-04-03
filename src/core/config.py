from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: Literal["dev", "prod"] = "dev"
    JWT_SECRET: str
    VERSION: str = "dev"
    DATABASE_URI: str = "postgresql+asyncpg://admin:admin@db:5432/highfive"
    OPENAI_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
