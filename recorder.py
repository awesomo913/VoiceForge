
import numpy as np
import sounddevice as sd


def get_input_devices() -> list[dict]:
    devices = sd.query_devices()
    return [
        {"index": i, "name": d["name"]}
        for i, d in enumerate(devices)
        if d["max_input_channels"] > 0
    ]


class Recorder:
    CHANNELS = 1
    DTYPE = np.float32

    def __init__(self, sample_rate: int = 48000, device: int | None = None):
        self.sample_rate = sample_rate
        self.device = device
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self.is_recording = False
        self.audio: np.ndarray | None = None

    def start(self) -> None:
        if self.is_recording:
            return
        self._frames = []
        self.is_recording = True

        def callback(indata: np.ndarray, frames: int, time, status) -> None:
            if status:
                import logging
                logging.warning(f"Recorder status: {status}")
            self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.CHANNELS,
            dtype=self.DTYPE,
            device=self.device,
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray | None:
        if not self.is_recording and not self._frames:
            return None
        self.is_recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._frames:
            return None
        audio = np.concatenate(self._frames, axis=0).squeeze()
        self.audio = audio
        return audio
