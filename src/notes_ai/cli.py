"""Rich Click command-line interface for Notes AI."""

from pathlib import Path

import rich_click as click

from notes_ai.interfaces.exceptions import ConfigurationError
from notes_ai.main import run

CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "rich_help_config": {
        "text_markup": "rich",
        "show_arguments": True,
        "group_arguments_options": True,
    },
}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("sources", nargs=-1, required=True, metavar="SOURCE...")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path("output"),
    show_default=True,
    help="Directory where generated Markdown notes are saved.",
)
@click.option(
    "--name",
    "-n",
    help="Custom note name; valid only when processing one source.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable debug logging.",
)
@click.option(
    "--tracing",
    "-t",
    is_flag=True,
    help="Enable Arize Phoenix tracing.",
)
def cli(
    sources: tuple[str, ...],
    output_dir: Path,
    name: str | None,
    verbose: bool,
    tracing: bool
) -> None:
    """Generate structured study notes from SOURCE URLs or local files."""
    if name and len(sources) != 1:
        raise click.UsageError("--name can only be used with a single source")

    try:
        run(
            sources,
            output_dir=output_dir,
            name=name,
            verbose=verbose,
            tracing=tracing,
            is_cli=True
        )
    except ConfigurationError as error:
        raise click.ClickException(str(error)) from error


if __name__ == "__main__":
    cli()