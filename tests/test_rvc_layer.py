import numpy as np
import sys
import os
import tempfile
from unittest.mock import patch
from params import VoiceParams
from effects.rvc_layer import apply_rvc

SR = 48000


def make_audio(duration=1.0):
    t = np.linspace(0, duration, int(SR * duration), dtype=np.float32)
    return np.sin(2 * np.pi * 220.0 * t)


def test_disabled_returns_input_unchanged():
    audio = make_audio()
    params = VoiceParams()
    params.rvc.enabled = False
    result = apply_rvc(audio, SR, params)
    np.testing.assert_array_equal(result, audio)


def test_no_model_path_returns_input():
    audio = make_audio()
    params = VoiceParams()
    params.rvc.enabled = True
    params.rvc.model_path = ""
    result = apply_rvc(audio, SR, params)
    np.testing.assert_array_equal(result, audio)


def test_nonexistent_model_path_returns_input():
    audio = make_audio()
    params = VoiceParams()
    params.rvc.enabled = True
    params.rvc.model_path = "C:/nonexistent/model.pth"
    result = apply_rvc(audio, SR, params)
    np.testing.assert_array_equal(result, audio)


def test_output_is_float32():
    audio = make_audio()
    params = VoiceParams()
    params.rvc.enabled = False
    result = apply_rvc(audio, SR, params)
    assert result.dtype == np.float32


def test_rvc_import_error_returns_input():
    """When rvc_python is not installed, apply_rvc must fall back gracefully."""
    audio = make_audio()
    params = VoiceParams()
    params.rvc.enabled = True

    # Use a real temp file so os.path.exists() passes, reaching the import
    with tempfile.NamedTemporaryFile(suffix=".pth", delete=False) as f:
        fake_model_path = f.name

    try:
        params.rvc.model_path = fake_model_path

        with patch.dict(sys.modules, {"rvc_python": None, "rvc_python.infer": None}):
            result = apply_rvc(audio, SR, params)
            np.testing.assert_array_equal(result, audio)
    finally:
        if os.path.exists(fake_model_path):
            os.unlink(fake_model_path)
