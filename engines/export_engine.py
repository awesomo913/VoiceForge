"""Export engine for VoiceForge.

Applies the full processing chain and writes a 24-bit WAV file:
  1. pyrubberband pitch + formant shift (consistent with preview engine)
  2. FFmpeg DSP filter chain: noise gate, de-esser, compressor+EQ, reverb+echo, loudnorm
  3. DeepFilterNet enhancement pass (optional, skipped if unavailable)
  4. RVC voice conversion pass (optional, skipped when disabled or model missing)
  5. Write 24-bit 48 kHz WAV via soundfile
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
            f"silenceremove=start_periods=1:start_threshold={dsp.gate_threshold_db}dB"
            f":stop_periods=-1:stop_threshold={dsp.gate_threshold_db}dB"
        )

    # De-esser: narrow EQ cut around the sibilance frequency (~7 kHz)
    if dsp.deesser_threshold_db > -60.0:
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
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", filter_str,
        "-ar", "48000",
        "-acodec", "pcm_s24le",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
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
            RuntimeError: If FFmpeg is not on PATH or exits non-zero.
            OSError:      If *output_path* cannot be written.
        """
        tmp_raw = tempfile.mktemp(suffix=".wav")
        tmp_ffmpeg_out = tempfile.mktemp(suffix=".wav")

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
            except Exception as exc:
                log.error("Export AI enhancement failed, passing through: %s", exc)

            # Step 4: RVC voice conversion (pass-through when disabled or model missing)
            try:
                enhanced = apply_rvc(enhanced, out_sr, params)
            except Exception as exc:
                log.error("Export RVC pass failed, passing through: %s", exc)

            # Step 5: Write 24-bit WAV
            sf.write(output_path, enhanced, out_sr, subtype="PCM_24")

        finally:
            for path in (tmp_raw, tmp_ffmpeg_out):
                if os.path.exists(path):
                    try:
                        os.unlink(path)
                    except OSError as exc:
                        log.warning("Could not remove temp file %s: %s", path, exc)
