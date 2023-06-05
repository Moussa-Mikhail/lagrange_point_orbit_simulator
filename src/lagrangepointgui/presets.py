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
if "sim_gui" in dir_path.parts:
    dir_path = dir_path.parent.parent

default_presets_path = os.path.join(dir_path, "default_presets.toml")
user_presets_path = os.path.join(dir_path, "user_presets.toml")

ParamPresets: TypeAlias = dict[str, dict[str, float | int]]
Constants: TypeAlias = dict[str, float | int]


def read_presets() -> tuple[ParamPresets, Constants]:
    default_params, default_consts = _read_preset(default_presets_path)
    user_params, user_consts = _read_preset(user_presets_path)

    return default_params | user_params, default_consts | user_consts


def _read_preset(file_path: str) -> tuple[ParamPresets, Constants]:
    with open(file_path, "rb") as file:
        presets = tomllib.load(file)

    params: dict[str, dict[str, float | int]] = presets.get("params", {})
    constants: dict[str, float | int] = presets.get("constants", {})

    return params, constants
