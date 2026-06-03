import numpy as np
import os
import tempfile
import soundfile as sf
from params import VoiceParams
from engines.export_engine import ExportEngine

SR = 48000


def make_audio(duration=0.5):
    t = np.linspace(0, duration, int(SR * duration), dtype=np.float32)
    return np.sin(2 * np.pi * 440.0 * t)


def test_export_creates_wav_file():
    engine = ExportEngine()
    audio = make_audio()
    params = VoiceParams()
    params.enhance.enabled = False
    params.rvc.enabled = False

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.wav")
        engine.export(audio, SR, params, out_path)
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0


def test_export_output_is_48khz():
    engine = ExportEngine()
    audio = make_audio()
    params = VoiceParams()
    params.enhance.enabled = False
    params.rvc.enabled = False

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.wav")
        engine.export(audio, SR, params, out_path)
        info = sf.info(out_path)
        assert info.samplerate == SR
