"""Build Ignition and Combustion configuration files from templates using Jinja2."""

import base64
import json
import os
import pathlib
import re
import secrets
import typing

import dotenv
import jinja2

FILES = pathlib.Path("files")
SYSTEMD = pathlib.Path("systemd")
OUTPUT_DIR = pathlib.Path("_build")
ENV_VARS = [
    "ROOT_PASSWD",
    "ADMIN_PASSWD",
    "ADMIN_SSH_KEYS",
    "ADMIN_TOTP",
    "DISK_PASSWD",
    "ADGUARD_MAC",
]


def gen_random_locally_administered_mac() -> str:
    """Generate a random locally administered MAC address.

    Returns:
        A string representing a random MAC address in the format
        "02:00:00:xx:xx:xx" where xx are random hexadecimal digits.
    """
    return "02:00:00:{:02x}:{:02x}:{:02x}".format(
        *[secrets.randbits(8) for _ in range(3)]
    )


def is_jinja(string: str) -> bool:
    """Check if a string contains Jinja2 template syntax.

    Args:
        string: The string to check.

    Returns:
        True if the string contains Jinja2 syntax, False otherwise.
    """
    return bool(re.search("{{.+}}", string) or re.search("{%.+%}", string))


def create_utf8_data_source(string: str) -> str:
    """Create a data source for UTF-8 encoded text.

    Args:
        string: The string to encode.

    Returns:
        A data URI containing the base64 encoded string.
    """
    input_bytes = string.encode(encoding="utf-8")
    data_bytes = base64.standard_b64encode(input_bytes)
    data = data_bytes.decode(encoding="ascii")
    return f"data:text/plain;charset=utf-8;base64,{data}"


class IgnitionBuilder:
    """Builds an Ignition configuration file from templates."""

    TEMPLATE_PATH = pathlib.Path("ignition/config.ign")
    """Path to the Ignition template file."""

    OUTPUT_PATH = OUTPUT_DIR.joinpath(TEMPLATE_PATH)
    """Path to the output Ignition configuration file."""

    def __init__(self, variables: dict[str, str]) -> None:
        """Initialise the IgnitionBuilder.

        Args:
            variables: Dictionary of variables to populate the Jinja2 templates.
        """
        self._vars = variables
        self._conf: dict[str, typing.Any] = {}

    def _first_pass(self) -> None:
        """Perform the first pass to populate the Ignition configuration."""
        template_source = self.TEMPLATE_PATH.read_text(encoding="utf-8")
        template = jinja2.Template(template_source)
        populated = template.render(**self._vars)
        self._conf = json.loads(populated)

    def _set_file_source(self, file: dict[str, typing.Any]) -> None:
        """Set the source for a file in the Ignition configuration.

        Args:
            file: A dictionary representing a file in the Ignition configuration.
        """
        source = file.get("contents", {}).get("source", "")
        if not source:
            source_file = FILES.joinpath(file["path"].lstrip("/"))
            content = source_file.read_text(encoding="utf-8")
        elif is_jinja(source):
            template = jinja2.Template(source)
            content = template.render(self._vars)
        else:
            return
        source = create_utf8_data_source(content)
        file["contents"]["source"] = source

    def _add_files(self) -> None:
        """Add files to the Ignition configuration."""
        for file in self._conf["storage"]["files"]:
            self._set_file_source(file)

    def _process_systemd_dropin(
        self, dropin: dict[str, str], overrides_dir: pathlib.Path
    ) -> None:
        """Process a systemd drop-in file.

        Args:
            dropin: A dictionary representing a systemd drop-in file.
            overrides_dir: The directory where the drop-in files are stored.
        """
        if not dropin["contents"]:
            dropin_file = overrides_dir.joinpath(dropin["name"])
            dropin["contents"] = dropin_file.read_text(encoding="utf-8")

    def _process_systemd_dropins(
        self, unit_name: str, dropins: list[dict[str, str]]
    ) -> None:
        """Process systemd drop-in files for a given unit.

        Args:
            unit_name: The name of the systemd unit.
            dropins: A list of drop-in files for the unit.
        """
        overrides_dir = SYSTEMD.joinpath(f"{unit_name}.d")
        for dropin in dropins:
            self._process_systemd_dropin(dropin, overrides_dir)

    def _add_systemd_overrides(self) -> None:
        """Add systemd overrides to the Ignition configuration."""
        for unit in self._conf["systemd"]["units"]:
            if dropins := unit.get("dropins"):
                unit_name = unit["name"].rsplit(".", maxsplit=1)[0]
                self._process_systemd_dropins(unit_name, dropins)

    def _write(self) -> None:
        """Write the Ignition configuration to the output file."""
        self.OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self.OUTPUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(self._conf, f, indent=2)

    def build(self) -> None:
        """Build the Ignition configuration file."""
        self._first_pass()
        self._add_files()
        self._add_systemd_overrides()
        self._write()


class CombustionBuilder:
    """Builds a Combustion script from templates."""

    TEMPLATE_PATH = pathlib.Path("combustion/script")
    """Path to the Combustion template file."""

    OUTPUT_PATH = OUTPUT_DIR.joinpath(TEMPLATE_PATH)
    """Path to the output Combustion script file."""

    def __init__(self, variables: dict[str, str]) -> None:
        """Initialise the CombustionBuilder.

        Args:
            variables: Dictionary of variables to populate the Jinja2 templates.
        """
        self._vars = variables

    def build(self) -> None:
        """Build the Combustion script file."""
        template_source = self.TEMPLATE_PATH.read_text(encoding="utf-8")
        template = jinja2.Template(template_source)
        populated = template.render(**self._vars)
        self.OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_PATH.write_text(populated, encoding="utf-8")


def main() -> None:
    """Build Ignition and Combustion configuration files."""
    dotenv.load_dotenv()
    jinja_vars = {i.lower(): os.environ[i] for i in ENV_VARS}
    jinja_vars.setdefault("adguard_mac", gen_random_locally_administered_mac())
    IgnitionBuilder(variables=jinja_vars).build()
    CombustionBuilder(variables=jinja_vars).build()


if __name__ == "__main__":
    main()
