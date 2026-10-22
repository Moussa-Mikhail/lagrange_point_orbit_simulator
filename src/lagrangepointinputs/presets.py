"""Reads default and user defined presets and constants for the GUI and the web UI."""

import os
import sys
import tomllib
from functools import lru_cache
from pathlib import Path

dir_path = Path(os.path.realpath(__file__)).parent

# if running from app set dir_path to the directory PyInstaller unpacks data files into (_internal)
# otherwise keep it as the directory of this module
if getattr(sys, "frozen", False):
    dir_path = Path(getattr(sys, "_MEIPASS", dir_path.parent.parent))


def _user_config_dir() -> Path:
    """Per-user config directory. Unlike the install directory it is writable and survives upgrades."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")

    return base / "lagrange-point-orbit-simulator"


default_presets_path = dir_path / "default_presets.toml"
user_presets_path = _user_config_dir() / "user_presets.toml"
# user_presets.toml used to live next to default_presets.toml. It is still read so existing files keep working.
legacy_user_presets_path = dir_path / "user_presets.toml"

type Expr = float | int | str
type Bases = list[str]

type ParamPresets = dict[str, dict[str, Expr | Bases]]
type Constants = dict[str, float | int]


def read_presets() -> tuple[ParamPresets, Constants]:
    default_params, default_consts = read_preset_file(default_presets_path)
    legacy_params, legacy_consts = read_preset_file(legacy_user_presets_path)
    user_params, user_consts = read_preset_file(user_presets_path)

    return default_params | legacy_params | user_params, default_consts | legacy_consts | user_consts


def read_preset_file(file_path: Path) -> tuple[ParamPresets, Constants]:
    try:
        modified_time = file_path.stat().st_mtime_ns
    except FileNotFoundError:
        return {}, {}

    return _read_preset_cached(file_path, modified_time)


# keyed on the modification time so edits to a presets file are picked up without restarting
@lru_cache(maxsize=8)
def _read_preset_cached(file_path: Path, modified_time: int) -> tuple[ParamPresets, Constants]:
    with Path.open(file_path, "rb") as file:
        presets = tomllib.load(file)

    params = presets.get("presets", {})
    constants = presets.get("constants", {})

    _check_constant_names(constants)

    return params, constants


def _check_constant_names(constants: dict[str, float | int]) -> None:
    names = sorted(constants, key=len)

    for i, maybe_substring in enumerate(names):
        for maybe_superstring in names[i + 1 :]:
            if maybe_substring in maybe_superstring:
                raise ValueError(
                    f'Constant name "{maybe_substring}" is a substring of "{maybe_superstring}". '
                    "Please rename one of them to avoid ambiguous parsing."
                )


def clear_cache() -> None:
    """Forget the files read so far, e.g. after writing one. The cache is keyed on the modification time, which can be
    too coarse to tell two quick writes apart.
    """
    _read_preset_cached.cache_clear()
