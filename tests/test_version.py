import tomllib
from pathlib import Path

from lagrangepointsimulator import app_version

PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def test_the_version_is_the_one_in_pyproject() -> None:
    assert app_version() == tomllib.loads(PYPROJECT.read_text())["project"]["version"]
