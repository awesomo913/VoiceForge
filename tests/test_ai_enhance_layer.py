import numpy as np
from unittest.mock import patch, MagicMock
from params import VoiceParams
from effects.ai_enhance_layer import apply_enhancement

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
