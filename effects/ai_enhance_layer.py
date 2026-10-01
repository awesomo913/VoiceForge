"""AI enhancement layer using DeepFilterNet for noise suppression and voice restoration."""
import logging
import os
import subprocess
import tempfile

import numpy as np

from params import VoiceParams

log = logging.getLogger(__name__)

_df_model = None
_df_state = None

# Lazy top-level import so patch("effects.ai_enhance_layer.enhance") works in tests.
try:
    from df.enhance import enhance  # noqa: F401 — re-exported for patching
except ImportError:
    enhance = None  # type: ignore[assignment]


def _get_df_model() -> tuple[object, object]:
    """Load (and cache) the DeepFilterNet model + state. Raises RuntimeError on failure."""
    global _df_model, _df_state
    if _df_model is None:
        try:
            from df.enhance import init_df
            _df_model, _df_state, _ = init_df()
        except Exception as exc:
            raise RuntimeError(f"DeepFilterNet failed to load: {exc}") from exc
    return _df_model, _df_state


def apply_enhancement(audio: np.ndarray, sr: int, params: VoiceParams) -> np.ndarray:
    """Apply AI-based audio enhancement (noise suppression) to *audio*.

    Returns the original array unchanged if enhancement is disabled or fails.
    """
    if not params.enhance.enabled:
        return audio

    try:
        import torch

        # Use the module-level `enhance` so tests can patch it easily.
        _enhance_fn = globals().get("enhance")
        if _enhance_fn is None:
            from df.enhance import enhance as _enhance_fn  # type: ignore[assignment]

        model, df_state = _get_df_model()
        target_sr: int = df_state.sr()

        working = audio.astype(np.float32)
        if sr != target_sr:
            working = _resample(working, sr, target_sr)

        tensor = torch.from_numpy(working)
        if tensor.dim() == 1:
            tensor = tensor.unsqueeze(0)

        # noise_suppression is 0–100; DeepFilterNet atten_lim is 0–40 dB.
        atten_lim_db = params.enhance.noise_suppression / 100.0 * 40.0

        enhanced = _enhance_fn(model, df_state, tensor, atten_lim_db=atten_lim_db)
        result: np.ndarray = enhanced.squeeze().numpy().astype(np.float32)

        if sr != target_sr:
            result = _resample(result, target_sr, sr)

        return result

    except Exception as exc:
        log.error("AI enhancement failed, passing through: %s", exc)
        return audio


def _resample(audio: np.ndarray, from_sr: int, to_sr: int) -> np.ndarray:
    """Resample *audio* from *from_sr* to *to_sr* via FFmpeg.

    Falls back to the original array and logs a warning if FFmpeg is not available.
    """
    import soundfile as sf

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_in = f.name
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_out = f.name
    try:
        sf.write(tmp_in, audio, from_sr, subtype="FLOAT")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_in, "-ar", str(to_sr), tmp_out],
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            log.warning("FFmpeg resampling failed (%s); returning un-resampled audio.", exc)
            return audio
        result, _ = sf.read(tmp_out, dtype="float32")
        return result
    finally:
        for path in (tmp_in, tmp_out):
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError as exc:
                    log.warning("Could not delete temp file %s: %s", path, exc)
