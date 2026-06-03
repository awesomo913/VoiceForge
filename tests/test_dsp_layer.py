import numpy as np
import pytest
from params import VoiceParams
from effects.dsp_layer import apply_dsp

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
