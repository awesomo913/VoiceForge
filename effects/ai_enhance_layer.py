"""AI enhancement layer using DeepFilterNet for noise suppression and voice restoration."""
import logging
import os
import subprocess
import sys
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


def _bundled_model_dir() -> str:
    """Path to the bundled DeepFilterNet3 model weights (assets/deepfilternet3/).

    Works both running from source (relative to this file's repo root) and
    frozen inside a PyInstaller onefile exe (relative to the temp extraction
    dir, sys._MEIPASS). Bundling these ~8.4 MB weights means init_df() never
    needs to reach the network on first run — see THIRD_PARTY.md for the
    exact source URL, version, and checksum of what's bundled.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", "deepfilternet3")


def _get_df_model() -> tuple[object, object]:
    """Load (and cache) the DeepFilterNet model + state. Raises RuntimeError on failure.

    Prefers the bundled model directory (assets/deepfilternet3/) when present;
    falls back to init_df()'s own default (its usual cache dir, downloading
    the model there on first use if needed) otherwise — e.g. for a from-source
    checkout where the bundled assets weren't fetched.
    """
    global _df_model, _df_state
    if _df_model is None:
        try:
            from df.enhance import init_df
            bundled_dir = _bundled_model_dir()
            model_base_dir = bundled_dir if os.path.isdir(bundled_dir) else None
            if model_base_dir is None:
                log.info(
                    "Bundled DeepFilterNet model not found at %s; "
                    "falling back to init_df()'s own default/download location.",
                    bundled_dir,
                )
            # log_file=None: VoiceForge already has its own diagnostics_logger
            # writing to %LOCALAPPDATA%; without this, init_df() writes its own
            # enhance.log directly into model_base_dir — which, for the
            # bundled case, is a tracked source directory (assets/deepfilternet3/),
            # so every from-source run would dirty the working tree with a log
            # file containing the developer's local file paths.
            _df_model, _df_state, _ = init_df(model_base_dir=model_base_dir, log_file=None)
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
    except ImportError as exc:
        log.error(
            "AI enhancement unavailable (torch not installed), passing through: %s",
            exc,
            extra={"ui_status": "AI noise cleanup unavailable — torch not installed"},
        )
        return audio

    try:
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
