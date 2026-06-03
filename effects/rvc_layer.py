"""RVC (Retrieval-based Voice Conversion) layer.

This is Layer 3 in the VoiceForge processing chain — runs last, only when
the user has a .pth model file loaded.

rvc-python is NOT installable on Windows (fairseq has no Windows wheel).
When the package is absent the layer silently passes audio through unchanged.
"""

import logging
import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf

from params import VoiceParams

log = logging.getLogger(__name__)


def apply_rvc(audio: np.ndarray, sr: int, params: VoiceParams) -> np.ndarray:
    """Apply RVC voice conversion, or pass through if not applicable.

    Falls back to returning the original audio when:
    - RVC is disabled in params
    - No model path is configured
    - The model file does not exist on disk
    - rvc_python is not installed (Windows limitation)
    - Any runtime error occurs during inference
    """
    if not params.rvc.enabled:
        return audio

    rvc = params.rvc
    if not rvc.model_path or not os.path.exists(rvc.model_path):
        log.warning("RVC layer enabled but no valid model_path — skipping")
        return audio

    try:
        from rvc_python.infer import RVCInference  # type: ignore[import]
    except ImportError:
        log.warning("rvc_python not installed (Windows limitation) — RVC layer skipped")
        return audio

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_in = f.name
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_out = f.name

    try:
        sf.write(tmp_in, audio.astype(np.float32), sr, subtype="FLOAT")

        infer = RVCInference(device="cpu")
        infer.load_model(rvc.model_path, rvc.index_path or None)
        infer.infer_file(
            input_path=tmp_in,
            output_path=tmp_out,
            f0_up_key=int(rvc.pitch_offset),
            index_rate=rvc.index_rate,
            filter_radius=rvc.filter_radius,
            rms_mix_rate=rvc.rms_mix_rate,
            protect=rvc.protect_rate,
            f0_method=rvc.f0_method,
        )

        result, out_sr = sf.read(tmp_out, dtype="float32")
        if out_sr != sr:
            result = _resample_ffmpeg(result, out_sr, sr)

        return result.astype(np.float32)

    except Exception as exc:
        log.error("RVC layer failed, passing through: %s", exc)
        return audio

    finally:
        for path in (tmp_in, tmp_out):
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError as exc:
                    log.warning("Failed to delete temp file %s: %s", path, exc)


def _resample_ffmpeg(audio: np.ndarray, from_sr: int, to_sr: int) -> np.ndarray:
    """Resample audio from from_sr to to_sr using ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_in = f.name
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_out = f.name
    try:
        sf.write(tmp_in, audio, from_sr, subtype="FLOAT")
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_in, "-ar", str(to_sr), tmp_out],
            check=True,
            capture_output=True,
        )
        result, _ = sf.read(tmp_out, dtype="float32")
        return result
    except OSError as exc:
        log.error("RVC resample failed (OS error): %s", exc)
        return audio
    except subprocess.CalledProcessError as exc:
        log.error("RVC resample failed (ffmpeg error): %s", exc)
        return audio
    except Exception as exc:
        log.error("RVC resample failed: %s", exc)
        return audio
    finally:
        for path in (tmp_in, tmp_out):
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError as exc:
                    log.warning("Failed to delete temp file %s: %s", path, exc)
