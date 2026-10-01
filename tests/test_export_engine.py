import os
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import soundfile as sf

import engines.export_engine as export_engine
from engines.export_engine import ExportEngine, _build_ffmpeg_filter, _run_ffmpeg_chain
from params import VoiceParams

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


# --- Argument-building: mocked subprocess, no real ffmpeg involved ------------


def test_run_ffmpeg_chain_invokes_resolved_binary_not_bare_ffmpeg():
    """The command passed to subprocess.run must use _resolve_ffmpeg_binary()'s
    result (the bundled imageio-ffmpeg exe in normal operation), not a
    hardcoded 'ffmpeg' string — this is the actual CI-breaking regression
    this test guards against. No real ffmpeg process is ever started here."""
    params = VoiceParams()
    fake_exe = r"C:\fake\imageio_ffmpeg\ffmpeg.exe"

    with patch.object(export_engine, "_resolve_ffmpeg_binary", return_value=fake_exe), \
         patch.object(export_engine.subprocess, "run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr=b"")
        _run_ffmpeg_chain("in.wav", "out.wav", params)

    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == fake_exe
    assert "-i" in cmd and cmd[cmd.index("-i") + 1] == "in.wav"
    assert cmd[-1] == "out.wav"


def test_run_ffmpeg_chain_raises_runtime_error_on_nonzero_exit():
    params = VoiceParams()
    with patch.object(export_engine, "_resolve_ffmpeg_binary", return_value="ffmpeg"), \
         patch.object(export_engine.subprocess, "run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr=b"boom")
        try:
            _run_ffmpeg_chain("in.wav", "out.wav", params)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as exc:
            assert "boom" in str(exc)


def test_run_ffmpeg_chain_raises_runtime_error_when_binary_missing():
    params = VoiceParams()
    with patch.object(export_engine, "_resolve_ffmpeg_binary", return_value="ffmpeg"), \
         patch.object(export_engine.subprocess, "run", side_effect=OSError("not found")):
        try:
            _run_ffmpeg_chain("in.wav", "out.wav", params)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as exc:
            assert "not found" in str(exc)


def test_build_ffmpeg_filter_always_includes_loudnorm():
    params = VoiceParams()
    assert "loudnorm" in _build_ffmpeg_filter(params)


def test_build_ffmpeg_filter_adds_gate_when_threshold_raised():
    params = VoiceParams()
    params.dsp.gate_threshold_db = -40.0
    assert "silenceremove" in _build_ffmpeg_filter(params)


def test_resolve_ffmpeg_binary_falls_back_to_path_on_resolution_failure():
    with patch.object(export_engine, "imageio_ffmpeg") as mock_mod:
        mock_mod.get_ffmpeg_exe.side_effect = RuntimeError("no ffmpeg exe could be found")
        assert export_engine._resolve_ffmpeg_binary() == "ffmpeg"


def test_resolve_ffmpeg_binary_retries_after_a_transient_failure():
    """Regression test: _resolve_ffmpeg_binary() must NOT cache the "ffmpeg"
    fallback — a transient resolution failure (e.g. the bundled binary
    briefly locked during first-run extraction) should not permanently
    prevent later calls from finding the real bundled binary."""
    with patch.object(export_engine, "imageio_ffmpeg") as mock_mod:
        mock_mod.get_ffmpeg_exe.side_effect = RuntimeError("transient")
        assert export_engine._resolve_ffmpeg_binary() == "ffmpeg"

        mock_mod.get_ffmpeg_exe.side_effect = None
        mock_mod.get_ffmpeg_exe.return_value = r"C:\real\ffmpeg.exe"
        assert export_engine._resolve_ffmpeg_binary() == r"C:\real\ffmpeg.exe"


# --- Real end-to-end tests using the actual bundled imageio-ffmpeg binary -----
# These never touch a system-installed ffmpeg: imageio-ffmpeg's own binary
# (pinned in requirements.txt) is what _resolve_ffmpeg_binary() resolves to.


def test_export_end_to_end_wav_real_ffmpeg():
    """Full ExportEngine.export() run, writing WAV — the final write is
    soundfile.write() (never FFmpeg), but step 2's DSP filter chain does run
    the real bundled ffmpeg binary against a live noise-gate setting."""
    engine = ExportEngine()
    audio = make_audio()
    params = VoiceParams()
    params.enhance.enabled = False
    params.rvc.enabled = False
    params.dsp.gate_threshold_db = -40.0  # exercise a real ffmpeg filter, not just loudnorm

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.wav")
        engine.export(audio, SR, params, out_path)
        assert os.path.exists(out_path)
        data, sr = sf.read(out_path)
        assert sr == SR
        assert len(data) > 0


def test_mp3_export_using_imageio_ffmpeg_binary():
    """VoiceForge's own export pipeline only ever writes WAV (see
    ExportEngine.export()) — there is no MP3 export feature in the app. This
    test instead proves the bundled imageio-ffmpeg binary itself (the thing
    this CI fix makes available with no system install) can actually encode
    MP3 end to end, which is what 'no system ffmpeg needed' is supposed to
    guarantee for any future format support."""
    ffmpeg_exe = export_engine._resolve_ffmpeg_binary()

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = os.path.join(tmpdir, "in.wav")
        mp3_path = os.path.join(tmpdir, "out.mp3")
        sf.write(wav_path, make_audio(), SR, subtype="PCM_16")

        result = subprocess.run(
            [ffmpeg_exe, "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "128k", mp3_path],
            capture_output=True,
            timeout=60,
        )

        assert result.returncode == 0, result.stderr.decode(errors="replace")
        assert os.path.exists(mp3_path)
        assert os.path.getsize(mp3_path) > 0
        # Sanity-check it's a real, decodable MP3, not just a non-empty file.
        with open(mp3_path, "rb") as f:
            header = f.read(3)
        assert header == b"ID3" or header[:2] == b"\xff\xfb"
