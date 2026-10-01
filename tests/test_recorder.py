from unittest.mock import patch

import numpy as np

from recorder import Recorder, get_input_devices


def test_recorder_initial_state():
    r = Recorder(sample_rate=48000)
    assert r.audio is None
    assert not r.is_recording


def test_stop_with_no_frames_returns_none():
    r = Recorder(sample_rate=48000)
    result = r.stop()
    assert result is None


def test_stop_concatenates_frames():
    r = Recorder(sample_rate=48000)
    fake_frames = [np.ones((1024, 1), dtype=np.float32) for _ in range(3)]
    r._frames = fake_frames
    r.is_recording = False
    audio = r.stop()
    assert isinstance(audio, np.ndarray)
    assert len(audio) == 3072
    assert audio.dtype == np.float32


def test_get_input_devices_returns_list():
    with patch("sounddevice.query_devices") as mock_q:
        mock_q.return_value = [
            {"name": "Microphone", "max_input_channels": 1, "index": 0},
            {"name": "Speakers", "max_input_channels": 0, "index": 1},
        ]
        devices = get_input_devices()
        assert isinstance(devices, list)
        assert len(devices) == 1  # only mic, not speakers
        assert devices[0]["name"] == "Microphone"
