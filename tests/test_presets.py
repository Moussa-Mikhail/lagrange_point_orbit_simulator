import os
from pathlib import Path

import pytest

from lagrangepointinputs import presets, user_presets
from lagrangepointinputs.safe_eval import safe_eval


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


# user_presets: editing the user's file


def test_save_preset_roundtrips(user_file: Path) -> None:
    user_presets.save_preset("Mine", {"star mass": "sun_mass/2", "initial speed": "0.9", "perturbation angle": ""})

    params = presets.read_presets()[0]
    assert params["Mine"] == {"star mass": "sun_mass/2", "initial speed": "0.9", "perturbation angle": ""}
    assert user_presets.user_preset_names() == ["Mine"]
    assert "Default" in params


def test_quick_saves_are_not_served_from_the_cache(user_file: Path) -> None:
    user_presets.save_preset("A", {"star mass": "1"})
    user_presets.save_preset("B", {"star mass": "2"})

    assert {"A", "B"} <= set(presets.read_presets()[0])


def test_saving_a_name_twice_replaces_it(user_file: Path) -> None:
    user_presets.save_preset("Mine", {"star mass": "1"})
    user_presets.save_preset(" Mine ", {"star mass": "2"})

    assert presets.read_presets()[0]["Mine"] == {"star mass": "2"}


def test_delete_preset(user_file: Path) -> None:
    user_presets.save_preset("Mine", {"star mass": "1"})
    user_presets.delete_preset("Mine")

    assert "Mine" not in presets.read_presets()[0]


def test_deleting_an_override_brings_back_the_default(user_file: Path) -> None:
    user_presets.save_preset("Sun Earth", {"star mass": "1"})
    assert presets.read_presets()[0]["Sun Earth"] == {"star mass": "1"}

    user_presets.delete_preset("Sun Earth")

    assert presets.read_presets()[0]["Sun Earth"]["star mass"] == "sun_mass"


def test_default_presets_cannot_be_deleted(user_file: Path) -> None:
    with pytest.raises(user_presets.PresetError, match="not one of your presets"):
        user_presets.delete_preset("Default")


def test_a_preset_that_is_a_base_cannot_be_deleted(user_file: Path) -> None:
    user_presets.save_text('[presets]\n"A" = { "star mass" = "1" }\n"B" = { bases = ["A"] }\n')

    with pytest.raises(user_presets.PresetError, match="base of 'B'"):
        user_presets.delete_preset("A")


COMMENTED = """\
# my presets
[constants]
my_mass = 2.0  # kg, roughly

[presets]
# the first one
"A" = { "star mass" = "1" }
"B" = { bases = ["A"], "initial speed" = 0.5 }
# trailing comment

[other_notes]
"""


def test_saving_keeps_comments_and_replaces_only_its_own_line(user_file: Path) -> None:
    user_file.write_text(COMMENTED.replace("\n[other_notes]\n", ""))

    user_presets.save_preset("A", {"star mass": "2"})
    user_presets.save_preset("C", {"star mass": "3"})

    lines = user_file.read_text().splitlines()
    assert lines[:6] == COMMENTED.splitlines()[:6]
    assert lines[6] == '"A" = { "star mass" = "2" }'
    assert lines[7] == '"B" = { bases = ["A"], "initial speed" = 0.5 }'
    assert lines[8] == '"C" = { "star mass" = "3" }'
    assert lines[9:] == ["# trailing comment"]
    assert user_presets.user_preset_names() == ["A", "B", "C"]


def test_a_new_section_is_added_when_there_is_none(user_file: Path) -> None:
    user_file.write_text("# just constants\n[constants]\nmy_mass = 2.0\n")

    user_presets.save_preset("A", {"star mass": "my_mass"})

    assert (
        user_file.read_text()
        == '# just constants\n[constants]\nmy_mass = 2.0\n\n[presets]\n"A" = { "star mass" = "my_mass" }\n'
    )


def test_deleting_keeps_comments(user_file: Path) -> None:
    user_file.write_text(COMMENTED.replace("\n[other_notes]\n", ""))

    user_presets.delete_preset("B")

    assert user_file.read_text() == COMMENTED.replace("\n[other_notes]\n", "").replace(
        '"B" = { bases = ["A"], "initial speed" = 0.5 }\n', ""
    )


def test_unusual_names_roundtrip(user_file: Path) -> None:
    name = 'Odd "name" \\ é'
    user_presets.save_preset(name, {"star mass": "1"})
    user_presets.save_preset(name, {"star mass": "2"})

    assert user_presets.user_preset_names() == [name]
    assert presets.read_presets()[0][name] == {"star mass": "2"}


def test_a_preset_defined_as_a_table_is_not_changed_behind_the_users_back(user_file: Path) -> None:
    text = '[presets."T"]\n"star mass" = "1"\n'
    user_file.write_text(text)

    with pytest.raises(user_presets.PresetError, match="Use Edit"):
        user_presets.save_preset("T", {"star mass": "2"})
    with pytest.raises(user_presets.PresetError, match="Use Edit"):
        user_presets.delete_preset("T")

    assert user_file.read_text() == text


def test_the_example_text_is_valid() -> None:
    assert user_presets.parse(user_presets.EXAMPLE_TEXT) == ({}, {})


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[presets", "Not valid TOML"),
        ("[other]\nx = 1\n", "Unknown section"),
        ('[presets]\n"A" = { "star mas" = 1 }\n', "unknown parameter"),
        ('[presets]\n"A" = { "star mass" = true }\n', "number or text"),
        ('[presets]\n"A" = { bases = ["Missing"] }\n', "unknown base"),
        ('[presets]\n"A" = { bases = ["B"] }\n"B" = { bases = ["A"] }\n', "loop"),
        ('[presets]\n"A" = { "Lagrange label" = "L9" }\n', "Lagrange label"),
        ('[presets]\n"A" = 3\n', "table"),
        ("[constants]\n1bad = 1\n", "valid constant name"),
        ('[constants]\nx = "text"\n', "must be a number"),
        ("[constants]\nab = 1\nabc = 2\n", "ambiguous"),
        ("[constants]\nmass = 1\n", "ambiguous"),
    ],
)
def test_invalid_text_is_rejected_and_the_file_is_left_alone(user_file: Path, text: str, message: str) -> None:
    user_presets.save_preset("Keep", {"star mass": "1"})
    before = user_file.read_text()

    with pytest.raises(user_presets.PresetError, match=message):
        user_presets.save_text(text)

    assert user_file.read_text() == before
