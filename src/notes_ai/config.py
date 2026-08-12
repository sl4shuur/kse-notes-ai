"""Application settings and runtime preparation helpers."""

from functools import lru_cache
from pathlib import Path
from pprint import pprint
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="APP_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "notes-ai"

    root_dir: Path = PROJECT_ROOT
    log_dir: Path = PROJECT_ROOT / "logs"
    output_dir: Path = PROJECT_ROOT / "output"
    temp_audio_dir: Path = PROJECT_ROOT / "temp_audio_chunks"
    directories: tuple[Path, ...] = (
        log_dir,
        output_dir,
        temp_audio_dir,
    )

    log_level: str = "INFO"
    log_formatter: Literal["ColoredFormatter", "FullColoredFormatter"] = "ColoredFormatter"
    log_date_format: str = "%d-%m-%Y %H:%M:%S"
    log_full_color: bool = True
    log_include_function: bool = True
    success_level: int = 69

    groq_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GROQ_API_KEY", "APP_GROQ_API_KEY"),
    )
    phoenix_endpoint: str = Field(
                default="",
                validation_alias=AliasChoices("PHOENIX_ENDPOINT_URL", "APP_PHOENIX_ENDPOINT_URL"),
            )


def _prepare_runtime(config: Config) -> None:
    for directory in config.directories:
        directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def _setup_config() -> Config:
    return Config()


@lru_cache
def get_config() -> Config:
    from notes_ai.loggers import apply_logging_config

    config = _setup_config()
    _prepare_runtime(config)
    apply_logging_config(config)
    return config


if __name__ == "__main__":
    pprint(get_config().model_dump(exclude={"groq_api_key"}))
