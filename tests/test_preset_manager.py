import json
import os

import pytest

from params import VoiceParams
from presets.manager import CATEGORIES, PresetManager, _slug

REAL_BUILTIN_DIR = os.path.join(os.path.dirname(__file__), "..", "presets", "builtin")


def make_mgr(tmp_path):
    return PresetManager(
        user_dir=str(tmp_path / "user"),
        builtin_dir=str(tmp_path / "builtin")
    )


def test_save_and_load_roundtrip(tmp_path):
    mgr = make_mgr(tmp_path)
    params = VoiceParams()
    params.dsp.pitch_semitones = -5.0
    params.dsp.clarity = 80.0
    mgr.save("Deep Voice", "My Voices", params)
    loaded = mgr.load("Deep Voice", "My Voices")
    assert loaded.dsp.pitch_semitones == -5.0
    assert loaded.dsp.clarity == 80.0


def test_list_presets_returns_saved(tmp_path):
    mgr = make_mgr(tmp_path)
    params = VoiceParams()
    mgr.save("Test Preset", "My Voices", params)
    listing = mgr.list_presets()
    assert "My Voices" in listing
    assert "Test Preset" in listing["My Voices"]


def test_delete_removes_preset(tmp_path):
    mgr = make_mgr(tmp_path)
    params = VoiceParams()
    mgr.save("Temp", "My Voices", params)
    mgr.delete("Temp", "My Voices")
    listing = mgr.list_presets()
    assert "Temp" not in listing.get("My Voices", [])


def test_load_nonexistent_raises(tmp_path):
    mgr = make_mgr(tmp_path)
    with pytest.raises(FileNotFoundError):
        mgr.load("Nonexistent", "My Voices")


def test_rename_works(tmp_path):
    mgr = make_mgr(tmp_path)
    params = VoiceParams()
    params.dsp.pitch_semitones = -3.0
    mgr.save("Old Name", "My Voices", params)
    mgr.rename("Old Name", "New Name", "My Voices")
    loaded = mgr.load("New Name", "My Voices")
    assert loaded.dsp.pitch_semitones == -3.0
    with pytest.raises(FileNotFoundError):
        mgr.load("Old Name", "My Voices")


def test_categories_are_correct():
    assert "My Voices" in CATEGORIES
    assert "Reel Personas" in CATEGORIES
    assert "Assistants" in CATEGORIES
    assert "Characters" in CATEGORIES


def test_real_builtin_preset_filenames_match_their_slug():
    """Regression test: PresetManager.load() resolves a built-in preset by
    re-slugging its display `name` and looking for `<slug>.json` on disk
    (see PresetManager._builtin_path). If a preset's `name` contains a
    character the slug doesn't map back onto the actual filename (e.g. a
    hyphen, which _slug() preserves instead of folding to '_'), loading that
    built-in by name raises FileNotFoundError even though the file exists.

    This previously bit "JARVIS-dark" (file jarvis_dark.json, slug
    jarvis-dark.json — mismatch) and "Siri-clean" (same issue), both since
    renamed to space-separated names that slug consistently. This test pins
    every shipped built-in preset so a future name doesn't reintroduce it.
    """
    assert os.path.isdir(REAL_BUILTIN_DIR), "presets/builtin directory is missing"
    json_files = sorted(f for f in os.listdir(REAL_BUILTIN_DIR) if f.endswith(".json"))
    assert len(json_files) >= 10, "expected the full set of built-in presets"

    for fname in json_files:
        with open(os.path.join(REAL_BUILTIN_DIR, fname), encoding="utf-8") as f:
            data = json.load(f)
        name = data["name"]
        expected_fname = f"{_slug(name)}.json"
        assert expected_fname == fname, (
            f"built-in preset {fname!r} has display name {name!r}, which "
            f"slugs to {expected_fname!r} — PresetManager.load({name!r}, ...) "
            f"would fail to find this file"
        )


def test_real_builtin_presets_all_loadable_by_name(tmp_path):
    """Every shipped built-in preset must be loadable through the same
    PresetManager.load() path the UI uses — not just present on disk."""
    mgr = PresetManager(user_dir=str(tmp_path / "user"), builtin_dir=REAL_BUILTIN_DIR)
    listing = mgr.list_presets()
    found_any = False
    for category, names in listing.items():
        for name in names:
            found_any = True
            params = mgr.load(name, category)
            assert isinstance(params, VoiceParams)
    assert found_any, "no built-in presets were discovered by list_presets()"


def test_no_trademarked_names_in_builtin_presets():
    """Preset names must stay generic — no third-party brand/celebrity names
    (see VoiceForge addendum: JARVIS and Siri were renamed for this reason)."""
    banned = ["jarvis", "siri", "alexa", "cortana", "hal 9000", "hal9000"]
    for fname in sorted(os.listdir(REAL_BUILTIN_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(REAL_BUILTIN_DIR, fname), encoding="utf-8") as f:
            data = json.load(f)
        name_lower = data["name"].lower()
        for term in banned:
            assert term not in name_lower, (
                f"{fname} preset name {data['name']!r} contains banned term {term!r}"
            )
