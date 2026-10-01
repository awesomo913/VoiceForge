import os
import sys
from unittest.mock import patch

import numpy as np

import effects.dsp_layer as dsp_layer
from effects.dsp_layer import _apply_pitch_formant, apply_dsp
from params import VoiceParams

SR = 48000


def make_audio(duration=1.0, freq=440.0):
    t = np.linspace(0, duration, int(SR * duration), dtype=np.float32)
    return np.sin(2 * np.pi * freq * t)


def test_passthrough_when_all_zero():
    audio = make_audio()
    params = VoiceParams()
    result = apply_dsp(audio, SR, params)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
    # When all DSP params are at zero/default, the audio should pass through unchanged.
    np.testing.assert_allclose(result, audio, rtol=1e-5, atol=1e-5)


def test_pitch_shift_changes_audio():
    audio = make_audio()
    params = VoiceParams()
    params.dsp.pitch_semitones = -4.0
    result = apply_dsp(audio, SR, params)
    assert result.shape[0] > 0
    assert not np.allclose(result[:len(audio)], audio[:len(result)])


def test_clarity_applies_without_error():
    audio = make_audio()
    params = VoiceParams()
    params.dsp.clarity = 80.0
    result = apply_dsp(audio, SR, params)
    assert result.shape[0] > 0


def test_reverb_applies_without_error():
    audio = make_audio()
    params = VoiceParams()
    params.dsp.reverb_wet = 0.3
    params.dsp.reverb_room = 0.5
    result = apply_dsp(audio, SR, params)
    assert result.shape[0] > 0


def test_output_is_float32():
    audio = make_audio()
    params = VoiceParams()
    params.dsp.pitch_semitones = -2.0
    params.dsp.clarity = 50.0
    result = apply_dsp(audio, SR, params)
    assert result.dtype == np.float32


def test_formant_fallback_surfaces_ui_status():
    """Regression test: when pyrubberband's rubberband binary isn't on PATH
    and a formant shift was requested, the fallback must tag the log record
    with a `ui_status` so the GUI's status-bar handler can tell the user —
    silently dropping formant shift with only a log line is easy to miss."""
    audio = make_audio()
    with patch("effects.dsp_layer.pyrb.pitch_shift", side_effect=RuntimeError("no rubberband")):
        with patch("effects.dsp_layer.log") as mock_log:
            result = _apply_pitch_formant(audio, SR, pitch_semitones=-2.0, formant_shift=1.5)

    assert result.shape[0] > 0
    assert mock_log.warning.called
    ui_statuses = [
        call.kwargs.get("extra", {}).get("ui_status")
        for call in mock_log.warning.call_args_list
    ]
    assert "Formant shift unavailable — install rubberband" in ui_statuses


def test_ensure_vendored_rubberband_on_path_noop_when_not_vendored(monkeypatch, tmp_path):
    """Default/expected state until a human completes the manual vendoring
    step in THIRD_PARTY.md: nothing to add, PATH is left untouched."""
    monkeypatch.setattr(dsp_layer, "__file__", str(tmp_path / "effects" / "dsp_layer.py"))
    if hasattr(sys, "_MEIPASS"):
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    original_path = os.environ.get("PATH", "")

    dsp_layer._ensure_vendored_rubberband_on_path()

    assert os.environ.get("PATH", "") == original_path


def test_ensure_vendored_rubberband_on_path_prepends_when_present(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    (repo_root / "effects").mkdir(parents=True)
    vendor_dir = repo_root / "vendor" / "rubberband"
    vendor_dir.mkdir(parents=True)
    monkeypatch.setattr(dsp_layer, "__file__", str(repo_root / "effects" / "dsp_layer.py"))
    if hasattr(sys, "_MEIPASS"):
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setenv("PATH", r"C:\existing\path")

    dsp_layer._ensure_vendored_rubberband_on_path()

    assert os.environ["PATH"].split(os.pathsep)[0] == str(vendor_dir)


def test_ensure_vendored_rubberband_on_path_uses_meipass_when_frozen(monkeypatch, tmp_path):
    frozen_root = tmp_path / "frozen"
    vendor_dir = frozen_root / "vendor" / "rubberband"
    vendor_dir.mkdir(parents=True)
    monkeypatch.setattr(sys, "_MEIPASS", str(frozen_root), raising=False)
    monkeypatch.setenv("PATH", r"C:\existing\path")

    dsp_layer._ensure_vendored_rubberband_on_path()

    assert os.environ["PATH"].split(os.pathsep)[0] == str(vendor_dir)
