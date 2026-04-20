from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: Literal["dev", "prod"] = "dev"
    JWT_SECRET: str
    VERSION: str = "dev"
    DATABASE_URI: str = "postgresql+asyncpg://admin:admin@db:5432/highfive"
    OPENAI_API_KEY: str
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def redis_opts(self) -> dict:
        return {"host": self.REDIS_HOST, "port": self.REDIS_PORT}


settings = Settings()
