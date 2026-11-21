import click

from app.importer import import_students


def register_commands(app) -> None:
    @app.cli.command("import-students")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    def import_students_command(path: str) -> None:
        """Import or update students from the school xlsx file."""
        result = import_students(path)
        click.echo(f"created={result.created} updated={result.updated} skipped={result.skipped}")
