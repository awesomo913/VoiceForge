import numpy as np
import customtkinter as ctk


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

        samples = self._audio
        n_points = min(len(samples), w)
        step = max(1, len(samples) // n_points)
        downsampled = samples[::step][:n_points]
        normalized = downsampled / (np.max(np.abs(downsampled)) + 1e-9)

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
