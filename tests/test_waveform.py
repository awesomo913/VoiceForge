import numpy as np

from ui.waveform import _normalize_for_display


def test_normal_audio_downsamples_to_width():
    audio = np.sin(np.linspace(0, 10, 1000)).astype(np.float32)
    result = _normalize_for_display(audio, width=100)
    assert result is not None
    assert len(result) <= 100
    assert np.max(np.abs(result)) <= 1.0001


def test_empty_array_returns_none_instead_of_crashing():
    """Regression test: samples.size==0 used to divide by zero (size // n_points
    with n_points == 0) instead of being guarded."""
    assert _normalize_for_display(np.array([]), width=100) is None


def test_zero_d_scalar_array_does_not_crash():
    """Regression test: a 0-d array has no len(), which used to raise TypeError."""
    scalar = np.array(0.5, dtype=np.float32)
    result = _normalize_for_display(scalar, width=100)
    assert result is not None
    assert len(result) == 1


def test_zero_width_returns_none():
    audio = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    assert _normalize_for_display(audio, width=0) is None


def test_silence_does_not_divide_by_zero():
    audio = np.zeros(500, dtype=np.float32)
    result = _normalize_for_display(audio, width=50)
    assert result is not None
    assert np.all(result == 0)


def test_width_larger_than_audio_still_works():
    audio = np.array([0.1, -0.2, 0.3], dtype=np.float32)
    result = _normalize_for_display(audio, width=1000)
    assert result is not None
    assert len(result) == 3
