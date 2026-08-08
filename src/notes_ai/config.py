"""Application settings and runtime preparation helpers."""

import logging
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
    data_dir: Path = PROJECT_ROOT / "data"
    log_dir: Path = PROJECT_ROOT / "logs"
    output_dir: Path = PROJECT_ROOT / "output"
    content_dir: Path = PROJECT_ROOT / "content"
    temp_audio_dir: Path = PROJECT_ROOT / "temp_audio_chunks"
    test_data_dir: Path = PROJECT_ROOT / "test_data"
    test_output_dir: Path = PROJECT_ROOT / "test_output"
    directories: tuple[Path, ...] = (
        data_dir,
        log_dir,
        output_dir,
        content_dir,
        temp_audio_dir,
        test_data_dir,
        test_output_dir,
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


def _prepare_runtime(config: Config) -> None:
    for directory in config.directories:
        directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_config() -> Config:
    from notes_ai.utils.logging_config import setup_logging
    from notes_ai.utils.loggers import CustomLogger

    config = Config()
    _prepare_runtime(config)
    setup_logging(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        full_color=config.log_full_color,
        include_function=config.log_include_function,
        logger_class=CustomLogger,
        logger_name=config.app_name,
    )
    return config


if __name__ == "__main__":
    pprint(get_config().model_dump(exclude={"groq_api_key"}))
