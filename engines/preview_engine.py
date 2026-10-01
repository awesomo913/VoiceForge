"""Preview engine chaining all three processing layers: DSP → AI Enhancement → RVC."""

import logging

import numpy as np
import sounddevice as sd

from effects.ai_enhance_layer import apply_enhancement
from effects.dsp_layer import apply_dsp
from effects.rvc_layer import apply_rvc
from params import VoiceParams

log = logging.getLogger(__name__)


class PreviewEngine:
    """Process audio through DSP → AI Enhancement → RVC chains and play.

    Each layer is wrapped in try/except so one failing layer doesn't crash
    the entire preview pipeline.
    """

    def __init__(self) -> None:
        """Initialize the preview engine."""
        pass

    def process(self, audio: np.ndarray, sr: int, params: VoiceParams) -> np.ndarray:
        """Process audio through all three layers in sequence.

        Args:
            audio: mono float32 audio array
            sr: sample rate in Hz
            params: VoiceParams controlling all layers

        Returns:
            Processed audio as float32 ndarray. If all layers fail,
            returns the input audio converted to float32.
        """
        # Layer 1: DSP (pitch, formants, vibrato, EQ, reverb, delay)
        try:
            result = apply_dsp(audio, sr, params)
        except Exception as e:
            log.error(f"DSP layer error in preview: {e}")
            result = audio.astype(np.float32)

        # Layer 2: AI Enhancement (noise suppression via DeepFilterNet)
        try:
            result = apply_enhancement(result, sr, params)
        except Exception as e:
            log.error(f"AI enhancement error in preview: {e}")

        # Layer 3: RVC (voice conversion)
        try:
            result = apply_rvc(result, sr, params)
        except Exception as e:
            log.error(f"RVC layer error in preview: {e}")

        return result.astype(np.float32)

    def play(self, audio: np.ndarray, sr: int) -> None:
        """Play audio to the default speaker.

        Args:
            audio: mono float32 audio array
            sr: sample rate in Hz
        """
        self.stop_playback()
        try:
            sd.play(audio, samplerate=sr)
        except Exception as e:
            log.error(f"Playback error: {e}")

    def stop_playback(self) -> None:
        """Stop any currently playing audio."""
        try:
            sd.stop()
        except Exception as e:
            logging.warning(f"stop_playback error (ignored): {e}")

    def process_and_play(
        self, audio: np.ndarray, sr: int, params: VoiceParams
    ) -> np.ndarray:
        """Process audio and immediately play it.

        This is the main entry point called from the GUI when the user
        clicks the Preview button.

        Args:
            audio: mono float32 audio array
            sr: sample rate in Hz
            params: VoiceParams controlling all layers

        Returns:
            Processed audio as float32 ndarray
        """
        processed = self.process(audio, sr, params)
        self.play(processed, sr)
        return processed
