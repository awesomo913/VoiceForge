import pytest
import tempfile
import os
from params import VoiceParams
from presets.manager import PresetManager, CATEGORIES


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
