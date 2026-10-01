import customtkinter as ctk
import numpy as np


def _normalize_for_display(audio: np.ndarray, width: int) -> np.ndarray | None:
    """Downsample and normalize *audio* to at most *width* points for drawing.

    Returns None when there's nothing drawable instead of letting the caller
    hit a crash: a 0-d (scalar) array has no len(), and an empty array would
    divide by zero when computing the downsample step (`size // n_points`
    with `n_points == 0`). Both are real inputs a caller can hand in (e.g.
    Recorder.stop() returning an empty/degenerate array), not just a
    theoretical edge case.
    """
    if width < 1:
        return None
    samples = np.atleast_1d(audio)
    if samples.size == 0:
        return None
    n_points = min(samples.size, width)
    step = max(1, samples.size // n_points)
    downsampled = samples[::step][:n_points]
    peak = np.max(np.abs(downsampled))
    return downsampled / (peak + 1e-9)


class WaveformWidget(ctk.CTkCanvas):
    BG = "#1a1a2e"
    LINE_COLOR = "#00d4aa"

    def __init__(self, parent, height=80, **kwargs):
        super().__init__(parent, height=height, bg=self.BG, highlightthickness=0, **kwargs)
        self._audio = None
        self.bind("<Configure>", self._on_resize)

    def draw(self, audio: np.ndarray):
        self._audio = audio
        self._render()

    def _on_resize(self, event):
        if self._audio is not None:
            self._render()

    def _render(self):
        self.delete("all")
        if self._audio is None:
            return
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return

        normalized = _normalize_for_display(self._audio, w)
        if normalized is None:
            return
        n_points = len(normalized)

        mid = h / 2
        amp = mid * 0.85
        coords = []
        for i, v in enumerate(normalized):
            x = i * (w / n_points)
            y = mid - v * amp
            coords.extend([x, y])

        if len(coords) >= 4:
            self.create_line(coords, fill=self.LINE_COLOR, width=1, smooth=True)
        self.create_line(0, mid, w, mid, fill="#333355", width=1, dash=(2, 4))
