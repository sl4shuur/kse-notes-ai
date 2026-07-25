"""CLI entrypoint — thin wrapper around ``src.cli``."""

from src.cli.app import cli, create_logger, main

__all__ = ["cli", "create_logger", "main"]

if __name__ == "__main__":
    main()
