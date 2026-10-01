"""Export engine for VoiceForge.

Applies the full processing chain and writes a 24-bit WAV file:
  1. pyrubberband pitch + formant shift (consistent with preview engine)
  2. FFmpeg DSP filter chain: noise gate, de-esser, compressor+EQ, reverb+echo, loudnorm
  3. DeepFilterNet enhancement pass (optional, skipped if unavailable)
  4. RVC voice conversion pass (optional, skipped when disabled or model missing)
  5. Write 24-bit 48 kHz WAV via soundfile

FFmpeg resolution: this module never requires a system-installed `ffmpeg` on
PATH. It prefers the self-contained binary bundled by the `imageio-ffmpeg`
wheel (see `_resolve_ffmpeg_binary()`) — the same binary a release exe ships,
via PyInstaller's `--collect-data=imageio_ffmpeg` in `build.py` — and only
falls back to a bare `ffmpeg` command if that package is somehow unavailable.
The final output write (step 5) never goes through FFmpeg at all; it's
`soundfile.write()` writing WAV directly, so even if FFmpeg were entirely
missing, only step 2's filters (not the file format itself) would be
affected. See THIRD_PARTY.md for the bundled FFmpeg build's license.
"""

import logging
import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf

from effects.ai_enhance_layer import apply_enhancement
from effects.dsp_layer import _apply_pitch_formant, _apply_vibrato
from effects.rvc_layer import apply_rvc
from params import VoiceParams

log = logging.getLogger(__name__)

try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover - imageio-ffmpeg is a pinned dependency
    imageio_ffmpeg = None
    log.warning(
        "imageio_ffmpeg not importable — falling back to a bare 'ffmpeg' on PATH. "
        "This should not happen in a normal install (see requirements.txt)."
    )


def _resolve_ffmpeg_binary() -> str:
    """Return the ffmpeg executable path used for the DSP filter chain.

    Prefers `imageio_ffmpeg.get_ffmpeg_exe()`, which resolves (in order) an
    `IMAGEIO_FFMPEG_EXE` env override, the binary bundled inside the
    `imageio-ffmpeg` wheel itself, a conda-installed ffmpeg, or a system
    `ffmpeg` on PATH — so a release build and CI never depend on the user
    having installed ffmpeg separately. Falls back to the bare string
    "ffmpeg" (relying on PATH, as before) only if `imageio_ffmpeg` isn't
    importable or its own resolution raises (e.g. truly nothing is
    available anywhere) — `_run_ffmpeg_chain`'s existing OSError handling
    turns that into the same clear RuntimeError either way.

    Deliberately NOT cached at this level: `imageio_ffmpeg.get_ffmpeg_exe()`
    already caches its own successful resolution internally, so wrapping
    this in another cache would add nothing on the happy path — but it would
    permanently lock in the "ffmpeg"-on-PATH fallback after a single
    transient failure (e.g. the bundled binary briefly locked by an AV
    scanner during first-run extraction), silently preventing every later
    export in the same process from ever retrying the bundled binary.
    """
    if imageio_ffmpeg is not None:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:
            log.warning(
                "imageio_ffmpeg.get_ffmpeg_exe() failed, falling back to PATH "
                "ffmpeg: %s", exc,
            )
    return "ffmpeg"


def _build_ffmpeg_filter(params: VoiceParams) -> str:
    """Assemble the ffmpeg -af filter string from DSP params.

    Each effect is only added when the relevant param is active (above its
    default/off threshold), so a flat-settings export produces minimal processing.
    """
    dsp = params.dsp
    filters: list[str] = []

    # Noise gate: silence regions below the threshold
    if dsp.gate_threshold_db > -60.0:
        filters.append(
            f"silenceremove=start_periods=1:start_threshold={dsp.gate_threshold_db}dB:start_duration=0.1"
            f":stop_periods=-1:stop_threshold={dsp.gate_threshold_db}dB:stop_duration=0.1"
        )

    # De-esser: narrow EQ cut around the sibilance frequency (~7 kHz)
    if dsp.deesser_threshold_db > -80.0:
        gain_db = max(-24.0, dsp.deesser_threshold_db)
        filters.append(
            f"equalizer=f={dsp.deesser_freq:.0f}:width_type=o:width=2:g={gain_db:.1f}"
        )

    # Clarity: gentle compression + presence boost at 4 kHz
    if dsp.clarity > 0:
        ratio = 1.0 + (dsp.clarity / 100.0) * 7.0
        filters.append(
            f"acompressor=threshold=-24dB:ratio={ratio:.1f}:attack=5:release=50"
        )
        presence_db = (dsp.clarity / 100.0) * 6.0
        filters.append(
            f"equalizer=f=4000:width_type=o:width=2:g={presence_db:.1f}"
        )

    # Warmth: low-shelf boost around 200 Hz
    if dsp.warmth > 0:
        warmth_db = (dsp.warmth / 100.0) * 6.0
        filters.append(
            f"equalizer=f=200:width_type=s:width=200:g={warmth_db:.1f}"
        )

    # Reverb via aecho (simple room simulation)
    if dsp.reverb_wet > 0:
        delay_ms = max(1, int(dsp.reverb_room * 100))
        filters.append(
            f"aecho=0.8:{1.0 - dsp.reverb_wet:.2f}:{delay_ms}:{dsp.reverb_wet:.2f}"
        )

    # Echo/delay
    if dsp.echo_wet > 0:
        filters.append(
            f"aecho=0.8:{1.0 - dsp.echo_wet:.2f}"
            f":{dsp.echo_delay_ms:.0f}:{dsp.echo_feedback:.2f}"
        )

    # Always normalize loudness to broadcast standard (-16 LUFS)
    filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

    return ",".join(filters)


def _run_ffmpeg_chain(input_path: str, output_path: str, params: VoiceParams) -> None:
    """Run the assembled FFmpeg filter chain.

    Raises RuntimeError with stderr output if FFmpeg returns a non-zero exit code.
    """
    filter_str = _build_ffmpeg_filter(params)
    cmd = [
        _resolve_ffmpeg_binary(), "-y",
        "-i", input_path,
        "-af", filter_str,
        "-ar", "48000",
        "-acodec", "pcm_s24le",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True)
    except OSError as e:
        raise RuntimeError(f"FFmpeg not found or not executable: {e}") from e
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed (exit {result.returncode}): "
            f"{result.stderr.decode(errors='replace')}"
        )


class ExportEngine:
    """Applies the full VoiceForge chain and writes a 24-bit 48 kHz WAV."""

    def export(
        self,
        audio: np.ndarray,
        sr: int,
        params: VoiceParams,
        output_path: str,
    ) -> None:
        """Process *audio* and write the result to *output_path*.

        Args:
            audio:       Mono float32 PCM array.
            sr:          Sample rate of *audio* (Hz).
            params:      VoiceParams controlling all processing stages.
            output_path: Destination path; directories must already exist.

        Raises:
            RuntimeError: If no FFmpeg binary can be resolved at all (bundled
                          or on PATH), or the resolved binary exits non-zero.
            OSError:      If *output_path* cannot be written.
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_raw = f.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_ffmpeg_out = f.name

        try:
            # Step 1: pyrubberband pitch + formant + vibrato
            dsp = params.dsp
            work = audio.astype(np.float32)
            work = _apply_pitch_formant(work, sr, dsp.pitch_semitones, dsp.formant_shift)
            work = _apply_vibrato(work, sr, dsp.vibrato_rate_hz, dsp.vibrato_depth)
            sf.write(tmp_raw, work, sr, subtype="FLOAT")

            # Step 2: FFmpeg DSP chain (noise gate → de-esser → comp/EQ → reverb → loudnorm)
            _run_ffmpeg_chain(tmp_raw, tmp_ffmpeg_out, params)

            # Step 3: DeepFilterNet noise suppression
            enhanced, out_sr = sf.read(tmp_ffmpeg_out, dtype="float32")
            try:
                enhanced = apply_enhancement(enhanced, out_sr, params)
            except Exception:
                log.exception("Export AI enhancement failed, passing through")

            # Step 4: RVC voice conversion (pass-through when disabled or model missing)
            try:
                enhanced = apply_rvc(enhanced, out_sr, params)
            except Exception:
                log.exception("Export RVC pass failed, passing through")

            # Step 5: Write 24-bit WAV
            sf.write(output_path, enhanced, out_sr, subtype="PCM_24")

        finally:
            for path in (tmp_raw, tmp_ffmpeg_out):
                if os.path.exists(path):
                    try:
                        os.unlink(path)
                    except OSError as exc:
                        log.warning("Could not remove temp file %s: %s", path, exc)
