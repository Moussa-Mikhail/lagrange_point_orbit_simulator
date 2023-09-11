# pylint: disable=missing-docstring
"""Reads user defined presets and constants for usage in GUI."""
from typing import TypeAlias

try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib

import os
from pathlib import Path

dir_path = Path(os.path.realpath(__file__)).parent
# if running from app set dir_path to the "sim_gui" directory
# otherwise keep it as the "lagrangepointgui" directory
if "sim_gui" in dir_path.parts:
    dir_path = dir_path.parent.parent

default_presets_path = dir_path / "default_presets.toml"
user_presets_path = dir_path / "user_presets.toml"

Expr: TypeAlias = float | int | str
Bases: TypeAlias = list[str]

ParamPresets: TypeAlias = dict[str, dict[str, Expr | Bases]]
Constants: TypeAlias = dict[str, float | int]


def read_presets() -> tuple[ParamPresets, Constants]:
    default_params, default_consts = _read_preset(default_presets_path)
    user_params, user_consts = _read_preset(user_presets_path)

    return default_params | user_params, default_consts | user_consts


def _read_preset(file_path: Path) -> tuple[ParamPresets, Constants]:
    try:
        with Path.open(file_path, "rb") as file:
            presets = tomllib.load(file)
    except FileNotFoundError:
        return {}, {}

    params = presets.get("presets", {})
    constants = presets.get("constants", {})

    return params, constants
