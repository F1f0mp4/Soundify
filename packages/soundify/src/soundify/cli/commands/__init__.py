"""CLI commands package."""

from soundify.cli.commands.download import download_cmd
from soundify.cli.commands.meta import meta_cmd
from soundify.cli.commands.tags import tags_cmd
from soundify.cli.commands.version import version_cmd

__all__ = ["download_cmd", "meta_cmd", "tags_cmd", "version_cmd"]
