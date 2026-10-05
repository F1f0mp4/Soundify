"""Version command."""

from importlib.metadata import version

import typer


def version_cmd() -> None:
    """Show the soundify version."""
    typer.echo(f"soundify {version('soundify')}")
