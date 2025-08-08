"""A CLI tool to view and decode Ignition configuration files."""

import base64
import collections.abc
import json
import pathlib
import typing

import typer


class IgnitionConfigInspector:
    """Tool to view and decode Ignition configuration files."""

    def __init__(self, path: pathlib.Path) -> None:
        """Load the Ignition configuration from a JSON file.

        Args:
            path: The path to the Ignition configuration file.
        """
        self.path = path
        with self.path.open(encoding="utf-8") as f:
            self.config = json.load(f)

    def _decode_file_content(self, file: dict[str, typing.Any]) -> str:
        """Decode the content of a file in the Ignition configuration.

        Args:
            file: The file dictionary from the Ignition configuration.

        Returns:
            The decoded content of the file.
        """
        content = file["contents"]["source"]
        if "base64" in content:
            encoded = content.partition("base64,")[2]
            return base64.standard_b64decode(encoded).decode()
        try:
            return content.split(",", 1)[1]
        except IndexError:
            return content

    def _print_file(self, file: dict[str, typing.Any]) -> None:
        """Print the contents of a single file in the Ignition configuration.

        Args:
            file: The file dictionary from the Ignition configuration.
        """
        path = file["path"]
        content = self._decode_file_content(file)
        octal_mode = f"{int(mode):o}" if (mode := file.get("mode")) else "?"
        title = f"{path} (mode: {octal_mode})"
        typer.echo(title)
        typer.echo("=" * 88)
        typer.echo(content)
        typer.echo("-" * 88)
        typer.echo("\n")

    def _get_files(self) -> collections.abc.Iterator[dict[str, typing.Any]]:
        """Yield all files defined in the Ignition configuration."""
        yield from self.config.get("storage", {}).get("files", [])

    def print_files(self) -> None:
        """Print the contents of all files in the Ignition configuration."""
        for file in self._get_files():
            self._print_file(file)

    def print_files_by_path(self, paths: collections.abc.Iterable[str]) -> None:
        """Print the contents of file with a specific path.

        Args:
            paths: The paths to filter files by.
        """
        paths = list(paths)  # Force to list, in case paths is generator.
        for file in self._get_files():
            if file["path"] in paths:
                self._print_file(file)

    def _print_systemd_dropin(
        self, unit: dict[str, typing.Any], dropin: dict[str, typing.Any]
    ) -> None:
        """Print the contents of a systemd dropin file.

        Args:
            unit: The systemd unit dictionary from the Ignition configuration.
            dropin: The dropin dictionary from the Ignition configuration.
        """
        name = dropin["name"]
        contents = dropin.get("contents", "No contents available.")
        typer.echo(f"Unit: {unit['name']}, Dropin: {name}")
        typer.echo("=" * 88)
        typer.echo(contents)
        typer.echo("-" * 88)
        typer.echo("\n")

    def _get_systemd_units(self) -> collections.abc.Iterator[dict[str, typing.Any]]:
        """Yield all systemd units defined in the Ignition configuration."""
        yield from self.config.get("systemd", {}).get("units", [])

    def print_systemd_dropins(self) -> None:
        """Print the systemd overrides from the Ignition configuration."""
        for unit in self._get_systemd_units():
            if dropins := unit.get("dropins"):
                for dropin in dropins:
                    self._print_systemd_dropin(unit, dropin)

    def print_systemd_dropins_by_unit(
        self, units: collections.abc.Iterable[str]
    ) -> None:
        """Print the systemd overrides for specific units.

        Args:
            units: The names of the systemd units to filter by.
        """
        for unit in self._get_systemd_units():
            if unit["name"] in units and (dropins := unit.get("dropins")):
                for dropin in dropins:
                    self._print_systemd_dropin(unit, dropin)


app = typer.Typer()


@app.callback()
def main(
    ctx: typer.Context,
    config: typing.Annotated[
        pathlib.Path,
        typer.Option(
            "--config",
            "-c",
            help="Path to the ignition config file.",
        ),
    ] = pathlib.Path("_build/ignition/config.ign"),
) -> None:
    """CLI for working with ignition configs."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = IgnitionConfigInspector(pathlib.Path(config))
    typer.echo()


@app.command("files")
def print_files(
    ctx: typer.Context,
    files: typing.Annotated[list[pathlib.Path] | None, typer.Argument()] = None,
) -> None:
    """Print out a list of decoded files from the ignition config."""
    config: IgnitionConfigInspector = ctx.obj.get("config")
    if files:
        config.print_files_by_path(str(file).lstrip("files") for file in files)
    else:
        config.print_files()
        typer.echo("Decoded all files from ignition config.")


@app.command("systemd-dropins")
def print_systemd_dropins(
    ctx: typer.Context,
    units: typing.Annotated[list[str] | None, typer.Argument()] = None,
) -> None:
    """Print out the systemd dropins from the ignition config."""
    config: IgnitionConfigInspector = ctx.obj.get("config")
    if units:
        config.print_systemd_dropins_by_unit(units)
    else:
        config.print_systemd_dropins()


if __name__ == "__main__":
    app()
