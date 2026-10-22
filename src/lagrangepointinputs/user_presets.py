"""Validates, writes and edits the user's presets file, for the GUI and the web UI.

The file is user_presets.toml in the user config directory, see presets.py. Presets that are saved from the form
rewrite the file in a fixed layout, so comments in it are lost. Editing the text keeps whatever is written.
"""

import json
import re
import tomllib
from pathlib import Path
from typing import cast

from lagrangepointinputs import presets
from lagrangepointinputs.parameters import LABEL_TO_ATTRIBUTE, LAGRANGE_LABEL, LAGRANGE_LABELS
from lagrangepointsimulator.constants import CONSTANTS

BASES = "bases"
_CONSTANT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

EXAMPLE_TEXT = """\
# Your own presets and constants. The format is the same as in default_presets.toml.
# Constants can be used in the parameter fields, e.g. my_mass.
# Bases are applied in the order they're written, overwriting existing values.
#
# [constants]
# my_mass = 2.0e30
#
# [presets]
# "My system" = { bases = ["Default"], "star mass" = "my_mass", "initial speed" = 0.95 }
"""


class PresetError(ValueError):
    """The presets are invalid. The message is meant to be shown to the user."""


def read_text() -> str:
    """Text of the user's presets file, empty if there isn't one."""
    try:
        return presets.user_presets_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def user_preset_names() -> list[str]:
    """Names of the presets in the user's file. Only these can be deleted."""
    return list(presets.read_preset_file(presets.user_presets_path)[0])


def save_text(text: str) -> None:
    """Replace the user's presets file with text. Raises PresetError, leaving the file alone, if it's invalid."""
    parse(text)

    path = presets.user_presets_path
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(text, encoding="utf-8")
    Path.replace(temp_path, path)

    # the cache is keyed on the modification time, which can be too coarse to tell two quick saves apart
    presets.clear_cache()


def save_preset(name: str, values: dict[str, str]) -> None:
    """Store values, which map parameter labels to field text, as the user preset name."""
    name = name.strip()
    if not name:
        msg = "The preset needs a name."
        raise PresetError(msg)

    params, constants = parse(read_text())
    params[name] = {**values}
    save_text(serialize(params, constants))


def delete_preset(name: str) -> None:
    """Remove the user preset name. A default preset it overrode shows again."""
    params, constants = parse(read_text())
    if name not in params:
        msg = f"'{name}' is not one of your presets."
        raise PresetError(msg)

    del params[name]
    overrides_default = name in presets.read_preset_file(presets.default_presets_path)[0]
    users = [other for other, preset in params.items() if name in _bases(preset)]
    if users and not overrides_default:
        msg = f"'{name}' can't be deleted because it is a base of {', '.join(f"'{u}'" for u in users)}."
        raise PresetError(msg)

    save_text(serialize(params, constants))


def serialize(params: presets.ParamPresets, constants: presets.Constants) -> str:
    lines = ["# Written by the app. Comments are not kept when presets are saved from the form.", ""]

    if constants:
        lines.append("[constants]")
        lines.extend(f"{name} = {value!r}" for name, value in constants.items())
        lines.append("")

    lines.append("[presets]")
    for name, preset in params.items():
        fields = ", ".join(f"{_quote(label)} = {_toml_value(value)}" for label, value in _bases_first(preset))
        lines.append(f"{_quote(name)} = {{ {fields} }}")

    return "\n".join(lines) + "\n"


def parse(text: str) -> tuple[presets.ParamPresets, presets.Constants]:
    """Check text as the contents of the user's presets file and return its presets and constants.

    Raises PresetError describing the first problem found.
    """
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        msg = f"Not valid TOML: {e}"
        raise PresetError(msg) from e

    if unknown := set(data) - {"presets", "constants"}:
        msg = f"Unknown section '{min(unknown)}'. Only [presets] and [constants] are used."
        raise PresetError(msg)

    constants = data.get("constants", {})
    params = data.get("presets", {})

    _check_constants(constants)
    _check_presets(params)

    return params, constants


def _check_constants(constants: dict) -> None:
    for name, value in constants.items():
        if not _CONSTANT_NAME.fullmatch(name):
            msg = f"'{name}' is not a valid constant name. Use letters, digits and underscores, not starting with a digit."
            raise PresetError(msg)
        if isinstance(value, bool) or not isinstance(value, int | float):
            msg = f"Constant '{name}' must be a number."
            raise PresetError(msg)

    others = set(CONSTANTS) | set(presets.read_preset_file(presets.default_presets_path)[1])
    for name in constants:
        for other in (others | set(constants)) - {name}:
            if name in other or other in name:
                msg = (
                    f"Constant name '{name}' is contained in '{other}' or the other way around. "
                    "Rename one of them to avoid ambiguous parsing."
                )
                raise PresetError(msg)


def _check_presets(user_params: dict) -> None:
    for name, preset in user_params.items():
        if not name.strip():
            msg = "A preset has an empty name."
            raise PresetError(msg)
        if not isinstance(preset, dict):
            msg = f"Preset '{name}' must be a table of parameters."
            raise PresetError(msg)

        for label, value in preset.items():
            _check_preset_value(name, label, value)

    known = set(presets.read_preset_file(presets.default_presets_path)[0]) | set(user_params)
    known |= set(presets.read_preset_file(presets.legacy_user_presets_path)[0])
    for name, preset in user_params.items():
        for base in _bases(preset):
            if base not in known:
                msg = f"Preset '{name}' uses the unknown base '{base}'."
                raise PresetError(msg)

    _check_no_cycles(user_params)


def _check_preset_value(name: str, label: str, value: object) -> None:
    if label == BASES:
        if not isinstance(value, list) or not all(isinstance(base, str) for base in value):
            msg = f"In preset '{name}', bases must be a list of preset names."
            raise PresetError(msg)
    elif label not in LABEL_TO_ATTRIBUTE:
        msg = f"Preset '{name}' has the unknown parameter '{label}'. Known: {', '.join(LABEL_TO_ATTRIBUTE)}."
        raise PresetError(msg)
    elif isinstance(value, bool) or not isinstance(value, str | int | float):
        msg = f"In preset '{name}', '{label}' must be a number or text."
        raise PresetError(msg)
    elif label == LAGRANGE_LABEL and value not in LAGRANGE_LABELS:
        msg = f"In preset '{name}', '{LAGRANGE_LABEL}' must be one of {', '.join(LAGRANGE_LABELS)}."
        raise PresetError(msg)


def _check_no_cycles(user_params: dict) -> None:
    all_params = presets.read_preset_file(presets.default_presets_path)[0] | user_params

    def visit(name: str, path: tuple[str, ...]) -> None:
        if name in path:
            msg = f"Presets use each other as bases in a loop: {' -> '.join((*path, name))}."
            raise PresetError(msg)
        for base in _bases(all_params.get(name, {})):
            visit(base, (*path, name))

    for name in user_params:
        visit(name, ())


def _bases(preset: dict) -> list[str]:
    return cast(list[str], preset.get(BASES, []))


def _bases_first(preset: dict) -> list[tuple[str, object]]:
    return sorted(preset.items(), key=lambda item: item[0] != BASES)


def _quote(text: str) -> str:
    return json.dumps(text)


def _toml_value(value: object) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_quote(str(item)) for item in value) + "]"
    if isinstance(value, str):
        return _quote(value)
    return repr(value)
