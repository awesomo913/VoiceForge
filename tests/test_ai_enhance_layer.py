import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np

import effects.ai_enhance_layer as ai_enhance_layer
from effects.ai_enhance_layer import apply_enhancement
from params import VoiceParams

SR = 48000


def make_audio(duration=1.0):
    t = np.linspace(0, duration, int(SR * duration), dtype=np.float32)
    return np.sin(2 * np.pi * 440.0 * t)


def test_disabled_returns_input_unchanged():
    audio = make_audio()
    params = VoiceParams()
    params.enhance.enabled = False
    result = apply_enhancement(audio, SR, params)
    np.testing.assert_array_equal(result, audio)


def test_enabled_with_mocked_deepfilter_returns_same_shape():
    audio = make_audio()
    params = VoiceParams()
    params.enhance.enabled = True

    mock_enhanced = MagicMock()
    mock_enhanced.squeeze.return_value.numpy.return_value = audio.copy()

    with patch("effects.ai_enhance_layer._get_df_model") as mock_get, \
         patch("effects.ai_enhance_layer.enhance") as mock_enhance:
        mock_model = MagicMock()
        mock_state = MagicMock()
        mock_state.sr.return_value = SR
        mock_get.return_value = (mock_model, mock_state)
        mock_enhance.return_value = mock_enhanced

        result = apply_enhancement(audio, SR, params)
        assert result.shape == audio.shape
        assert result.dtype == np.float32


def test_error_in_deepfilter_returns_original():
    audio = make_audio()
    params = VoiceParams()
    params.enhance.enabled = True

    with patch("effects.ai_enhance_layer._get_df_model") as mock_get:
        mock_get.side_effect = RuntimeError("DeepFilterNet failed")
        result = apply_enhancement(audio, SR, params)
        np.testing.assert_array_equal(result, audio)


def test_torch_missing_passes_through_and_surfaces_ui_status():
    """Regression test: when torch isn't installed, apply_enhancement must
    still pass audio through unchanged (not raise), and must tag the log
    record with a `ui_status` the GUI's status-bar handler surfaces to the
    user once — not just a line buried in the log file."""
    audio = make_audio()
    params = VoiceParams()
    params.enhance.enabled = True

    # Force `import torch` to raise ImportError regardless of whether torch is
    # actually installed in the environment running this test.
    with patch.dict(sys.modules, {"torch": None}):
        with patch("effects.ai_enhance_layer.log") as mock_log:
            result = apply_enhancement(audio, SR, params)

    np.testing.assert_array_equal(result, audio)
    assert mock_log.error.called
    _, kwargs = mock_log.error.call_args
    assert kwargs.get("extra", {}).get("ui_status") == (
        "AI noise cleanup unavailable — torch not installed"
    )


def test_bundled_model_dir_points_at_assets_deepfilternet3():
    path = ai_enhance_layer._bundled_model_dir()
    assert path.endswith(os.path.join("assets", "deepfilternet3"))


def test_bundled_model_dir_uses_meipass_when_frozen(monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", r"C:\fake\frozen\dir", raising=False)
    path = ai_enhance_layer._bundled_model_dir()
    assert path == os.path.join(r"C:\fake\frozen\dir", "assets", "deepfilternet3")


def test_get_df_model_passes_bundled_dir_to_init_df(monkeypatch, tmp_path):
    """Regression test: the model must load from the bundled assets dir when
    present, not silently fall back to init_df()'s own download/cache
    location (which would defeat the point of bundling it)."""
    ai_enhance_layer._df_model = None
    ai_enhance_layer._df_state = None
    fake_bundled_dir = tmp_path / "assets" / "deepfilternet3"
    fake_bundled_dir.mkdir(parents=True)
    monkeypatch.setattr(ai_enhance_layer, "_bundled_model_dir", lambda: str(fake_bundled_dir))

    mock_init_df = MagicMock(return_value=("model", "state", "suffix"))
    with patch.dict(sys.modules, {"df.enhance": MagicMock(init_df=mock_init_df)}):
        ai_enhance_layer._get_df_model()

    mock_init_df.assert_called_once_with(model_base_dir=str(fake_bundled_dir), log_file=None)
    ai_enhance_layer._df_model = None  # reset the module-level cache for other tests
    ai_enhance_layer._df_state = None


def test_get_df_model_falls_back_when_bundled_dir_missing(monkeypatch, tmp_path):
    ai_enhance_layer._df_model = None
    ai_enhance_layer._df_state = None
    missing_dir = tmp_path / "does_not_exist"
    monkeypatch.setattr(ai_enhance_layer, "_bundled_model_dir", lambda: str(missing_dir))

    mock_init_df = MagicMock(return_value=("model", "state", "suffix"))
    with patch.dict(sys.modules, {"df.enhance": MagicMock(init_df=mock_init_df)}):
        ai_enhance_layer._get_df_model()

    mock_init_df.assert_called_once_with(model_base_dir=None, log_file=None)
    ai_enhance_layer._df_model = None
    ai_enhance_layer._df_state = None
