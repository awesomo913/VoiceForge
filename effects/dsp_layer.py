import logging

import numpy as np
import pyrubberband as pyrb
from pedalboard import (
    Compressor,
    Delay,
    LowShelfFilter,
    NoiseGate,
    Pedalboard,
    PeakFilter,
    PitchShift,
    Reverb,
)

from params import VoiceParams

log = logging.getLogger(__name__)


def _apply_pitch_formant(
    audio: np.ndarray, sr: int, pitch_semitones: float, formant_shift: float
) -> np.ndarray:
    """Shift pitch and/or formants.

    Formants are the resonant frequency peaks that give a voice its character
    (makes a voice sound like a different person vs. just playing faster/slower).

    Primary path: pyrubberband CLI (requires the `rubberband` binary on PATH).
    When formant_shift is non-zero, a two-pass approach moves the resonances
    independently of the fundamental pitch.

    Fallback path: pedalboard.PitchShift (ships Rubber Band as a C++ lib, no
    external binary required). Formant shifting is unavailable in this mode —
    only the pitch_semitones shift is applied, and formant_shift is silently
    ignored with a warning.
    """
    if pitch_semitones == 0.0 and formant_shift == 0.0:
        return audio

    try:
        if formant_shift != 0.0:
            # Pass 1: shift pitch+formant together (--formant flag preserves the
            # ratio between pitch and formant, so formants follow the pitch shift)
            combined = pyrb.pitch_shift(
                audio.astype(np.float64),
                sr,
                n_steps=pitch_semitones + formant_shift,
                rbargs={"--formant": ""},
            )
            # Pass 2: shift pitch back by formant_shift amount, leaving formants
            # displaced by formant_shift semitones relative to original
            result = pyrb.pitch_shift(combined, sr, n_steps=-formant_shift)
        else:
            result = pyrb.pitch_shift(
                audio.astype(np.float64), sr, n_steps=pitch_semitones
            )
        return result.astype(np.float32)
    except RuntimeError as exc:
        # rubberband binary not found — fall back to pedalboard's built-in
        log.warning(
            "_apply_pitch_formant: pyrubberband unavailable (%s); "
            "falling back to pedalboard.PitchShift (formant_shift ignored)",
            exc,
        )
        if formant_shift != 0.0:
            log.warning(
                "_apply_pitch_formant: formant_shift=%.1f ignored in fallback mode",
                formant_shift,
            )
    except Exception as exc:
        log.warning("_apply_pitch_formant: unexpected error: %s", exc)

    # pedalboard fallback — pitch only, no formant adjustment
    try:
        shifter = PitchShift(semitones=pitch_semitones)
        return shifter(audio.astype(np.float32), sr)
    except Exception as exc:
        log.warning("_apply_pitch_formant: pedalboard fallback also failed: %s", exc)
        return audio.astype(np.float32)


def _apply_vibrato(
    audio: np.ndarray, sr: int, rate_hz: float, depth: float
) -> np.ndarray:
    """Apply a wobble (vibrato) effect by modulating a short delay with a sine LFO.

    rate_hz: how many wobbles per second (e.g. 5 Hz = 5 wobbles/sec)
    depth:   0–1 scale controlling max delay swing (1 = ~10ms max delay)
    """
    if depth == 0.0:
        return audio

    n = len(audio)
    t = np.arange(n, dtype=np.float32) / sr
    max_delay_samples = int(sr * 0.01 * depth)
    lfo = (np.sin(2 * np.pi * rate_hz * t) * 0.5 + 0.5) * max_delay_samples
    indices = np.arange(n, dtype=np.float32) - lfo
    indices = np.clip(indices, 0, n - 1)
    return np.interp(indices, np.arange(n), audio).astype(np.float32)


def apply_dsp(audio: np.ndarray, sr: int, params: VoiceParams) -> np.ndarray:
    """Run the full DSP chain on a mono float32 audio array.

    Processing order:
    1. Pitch / formant shift (time-domain via rubberband)
    2. Vibrato LFO delay modulation
    3. pedalboard plugin chain: noise gate → de-esser → clarity (compressor +
       presence EQ) → warmth (low-shelf) → reverb → echo/delay
    """
    dsp = params.dsp
    result = audio.astype(np.float32).copy()

    # --- Time-domain transforms (must happen before pedalboard) ---
    result = _apply_pitch_formant(result, sr, dsp.pitch_semitones, dsp.formant_shift)
    result = _apply_vibrato(result, sr, dsp.vibrato_rate_hz, dsp.vibrato_depth)

    # --- Build pedalboard plugin list ---
    plugins = []

    # Noise gate: cuts signal below threshold_db (silences quiet background noise)
    if dsp.gate_threshold_db > -60.0:
        plugins.append(
            NoiseGate(
                threshold_db=dsp.gate_threshold_db,
                attack_ms=dsp.gate_attack_ms,
                release_ms=dsp.gate_release_ms,
            )
        )

    # De-esser: narrow cut around sibilant frequencies (~7 kHz) to tame harsh S/T sounds
    if dsp.deesser_threshold_db > -60.0:
        plugins.append(
            PeakFilter(
                cutoff_frequency_hz=dsp.deesser_freq,
                gain_db=max(-24.0, dsp.deesser_threshold_db),
                q=5.0,
            )
        )

    # Clarity: gentle compression + presence boost makes voice cut through a mix
    if dsp.clarity > 0:
        ratio = 1.0 + (dsp.clarity / 100.0) * 7.0
        plugins.append(
            Compressor(
                threshold_db=-24.0, ratio=ratio, attack_ms=5.0, release_ms=50.0
            )
        )
        plugins.append(
            PeakFilter(
                cutoff_frequency_hz=4000.0,
                gain_db=(dsp.clarity / 100.0) * 6.0,
                q=1.0,
            )
        )

    # Warmth: boost low-mids (200 Hz shelf) to add body / reduce thinness
    if dsp.warmth > 0:
        plugins.append(
            LowShelfFilter(
                cutoff_frequency_hz=200.0,
                gain_db=(dsp.warmth / 100.0) * 6.0,
                q=0.7,
            )
        )

    # Reverb: adds room ambience — room_size controls decay length
    if dsp.reverb_wet > 0:
        plugins.append(
            Reverb(
                room_size=dsp.reverb_room,
                damping=dsp.reverb_damping,
                wet_level=dsp.reverb_wet,
                dry_level=1.0 - dsp.reverb_wet,
            )
        )

    # Echo/delay: repeat with feedback decay
    if dsp.echo_wet > 0:
        plugins.append(
            Delay(
                delay_seconds=dsp.echo_delay_ms / 1000.0,
                feedback=dsp.echo_feedback,
                mix=dsp.echo_wet,
            )
        )

    if plugins:
        board = Pedalboard(plugins)
        result = board(result, sr)

    return result.astype(np.float32)
