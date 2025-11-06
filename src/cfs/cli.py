"""Main CLI entry point for the CFS tool."""

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="cfs",
    help="Cursor File Structure (CFS) CLI - Manage Cursor instruction documents",
    add_completion=False,
)

# Create subcommand groups
instructions_app = typer.Typer(
    name="instructions",
    help="Manage Cursor instruction documents",
)
rules_app = typer.Typer(
    name="rules",
    help="Manage Cursor rules documents",
)

# Register subcommand groups
app.add_typer(instructions_app, name="instructions")
app.add_typer(rules_app, name="rules")


# Global options callback
@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
) -> None:
    """Main callback - shows help if no command provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def version() -> None:
    """Show the version number."""
    from cfs import __version__

    typer.echo(f"cfs version {__version__}")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
