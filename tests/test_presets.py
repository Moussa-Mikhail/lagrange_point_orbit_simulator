import os
from pathlib import Path

import pytest

from lagrangepointsimulator import presets
from lagrangepointsimulator.safe_eval import safe_eval


@pytest.fixture
def user_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "user_presets.toml"
    monkeypatch.setattr(presets, "user_presets_path", path)
    monkeypatch.setattr(presets, "legacy_user_presets_path", tmp_path / "legacy" / "user_presets.toml")
    return path


def test_default_presets_load() -> None:
    params, constants = presets.read_presets()

    assert "Default" in params
    assert "moon_mass" in constants


def test_user_presets_and_constants_are_merged(user_file: Path) -> None:
    user_file.write_text('[constants]\nmy_mass = 5.0\n[presets]\n"Mine" = { "star mass" = "my_mass" }\n')

    params, constants = presets.read_presets()

    assert "Mine" in params
    assert "Default" in params
    assert constants["my_mass"] == 5.0
    assert safe_eval("my_mass*2") == 10.0


def test_legacy_location_is_still_read(user_file: Path) -> None:
    legacy = presets.legacy_user_presets_path
    legacy.parent.mkdir()
    legacy.write_text('[presets]\n"Old" = { "star mass" = 1.0 }\n')

    assert "Old" in presets.read_presets()[0]


def test_edits_are_picked_up_without_restarting(user_file: Path) -> None:
    user_file.write_text('[presets]\n"First" = { "star mass" = 1.0 }\n')
    assert "First" in presets.read_presets()[0]

    user_file.write_text('[presets]\n"Second" = { "star mass" = 1.0 }\n')
    stat = user_file.stat()
    os.utime(user_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    params = presets.read_presets()[0]
    assert "Second" in params
    assert "First" not in params


def test_constant_names_cannot_contain_each_other(user_file: Path) -> None:
    user_file.write_text("[constants]\nab = 1.0\nabc = 2.0\n")

    with pytest.raises(ValueError):
        presets.read_presets()
