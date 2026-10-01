from unittest.mock import patch

import numpy as np

from engines.preview_engine import PreviewEngine
from params import VoiceParams

SR = 48000


def make_audio(duration=0.5):
    """Generate a simple sine wave test audio."""
    t = np.linspace(0, duration, int(SR * duration), dtype=np.float32)
    return np.sin(2 * np.pi * 440.0 * t)


def test_process_returns_ndarray():
    """Test that process() returns a numpy array."""
    engine = PreviewEngine()
    audio = make_audio()
    params = VoiceParams()
    params.enhance.enabled = False
    params.rvc.enabled = False
    result = engine.process(audio, SR, params)
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float32


def test_process_with_all_layers_disabled():
    """Test that process() returns non-empty audio even with all layers disabled."""
    engine = PreviewEngine()
    audio = make_audio()
    params = VoiceParams()
    params.enhance.enabled = False
    params.rvc.enabled = False
    result = engine.process(audio, SR, params)
    assert len(result) > 0


def test_stop_playback_when_not_playing_does_not_raise():
    """Test that stop_playback() doesn't crash when nothing is playing."""
    engine = PreviewEngine()
    engine.stop_playback()  # must not raise


def test_process_chains_dsp_then_enhance_then_rvc():
    """Verify layers are called in order: DSP → AI enhance → RVC."""
    engine = PreviewEngine()
    audio = make_audio()
    params = VoiceParams()

    call_order = []

    with patch("engines.preview_engine.apply_dsp") as mock_dsp, \
         patch("engines.preview_engine.apply_enhancement") as mock_enh, \
         patch("engines.preview_engine.apply_rvc") as mock_rvc:

        mock_dsp.side_effect = lambda a, s, p: (call_order.append("dsp"), a)[1]
        mock_enh.side_effect = lambda a, s, p: (call_order.append("enh"), a)[1]
        mock_rvc.side_effect = lambda a, s, p: (call_order.append("rvc"), a)[1]

        engine.process(audio, SR, params)

    assert call_order == ["dsp", "enh", "rvc"]
