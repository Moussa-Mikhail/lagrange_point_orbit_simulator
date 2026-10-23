"""The version of the package, which pyproject.toml defines."""

from importlib.metadata import PackageNotFoundError, version

PACKAGE_NAME = "lagrange-point-orbit-simulator"


def app_version() -> str:
    """The installed version, or "unknown" when the package's metadata isn't there."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"
