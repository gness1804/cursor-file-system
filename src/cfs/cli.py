"""Main CLI entry point for the CFS tool."""

import typer

app = typer.Typer(
    name="cfs",
    help="Cursor File Structure (CFS) CLI - Manage Cursor instruction documents",
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Main callback - shows help if no command provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def version():
    """Show the version number."""
    from cfs import __version__
    typer.echo(f"cfs version {__version__}")


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

