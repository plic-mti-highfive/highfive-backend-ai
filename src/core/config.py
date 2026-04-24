from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerConfig(BaseModel):
    """Configuration for a single BullMQ worker."""

    name: str
    queue: str
    concurrency: int = 1
    max_retries: int = 0
    retry_backoff_ms: int = 1000
    remove_on_complete: bool = True
    remove_on_fail: bool = False


class WorkersConfig(BaseModel):
    """Configuration for all workers."""

    workers: list[WorkerConfig] = Field(default_factory=list)


class Settings(BaseSettings):
    ENV: Literal["dev", "prod"] = "dev"
    JWT_SECRET: str
    VERSION: str = "dev"
    DATABASE_URI: str = "postgresql+asyncpg://admin:admin@db:5432/highfive"
    OPENAI_API_KEY: str
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    WORKERS_CONFIG_PATH: str = "config/workers.yaml"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def redis_opts(self) -> dict:
        return {"host": self.REDIS_HOST, "port": self.REDIS_PORT}

    def load_workers_config(self) -> WorkersConfig:
        """Load worker configuration from YAML file."""
        config_path = Path(self.WORKERS_CONFIG_PATH)
        if not config_path.exists():
            raise FileNotFoundError(f"Workers config file not found: {config_path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        return WorkersConfig(**data)


settings = Settings()
