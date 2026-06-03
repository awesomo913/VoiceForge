import customtkinter as ctk
from params import VoiceParams
from typing import Callable
import tkinter as tk


def _slider(parent, label: str, from_: float, to: float, initial: float,
            command: Callable, row: int, decimals: int = 1):
    ctk.CTkLabel(parent, text=label, anchor="w").grid(
        row=row, column=0, sticky="w", padx=8, pady=2)
    val_var = tk.StringVar(value=f"{initial:.{decimals}f}")
    slider = ctk.CTkSlider(
        parent, from_=from_, to=to, width=200,
        command=lambda v: (command(v), val_var.set(f"{v:.{decimals}f}"))
    )
    slider.set(initial)
    slider.grid(row=row, column=1, padx=8, pady=2)
    ctk.CTkLabel(parent, textvariable=val_var, width=50).grid(row=row, column=2, padx=4)
    return slider


class EffectsPanel(ctk.CTkFrame):
    def __init__(self, parent, params: VoiceParams, on_change: Callable, **kwargs):
        super().__init__(parent, **kwargs)
        self.params = params
        self.on_change = on_change
        self._sliders = {}
        self._build()

    def _build(self):
        self.tab_view = ctk.CTkTabview(self, width=480)
        self.tab_view.pack(fill="both", expand=True, padx=4, pady=4)
        self.tab_view.add("DSP Effects")
        self.tab_view.add("AI Enhancement")
        self.tab_view.add("AI Voice (RVC)")
        self._build_dsp_tab(self.tab_view.tab("DSP Effects"))
        self._build_enhance_tab(self.tab_view.tab("AI Enhancement"))
        self._build_rvc_tab(self.tab_view.tab("AI Voice (RVC)"))

    def _build_dsp_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True)
        dsp = self.params.dsp

        def s(label, attr, from_, to, row, decimals=1):
            sl = _slider(scroll, label, from_, to, getattr(dsp, attr),
                         lambda v, a=attr: (setattr(dsp, a, float(v)), self.on_change()),
                         row, decimals)
            self._sliders[f"dsp.{attr}"] = sl

        s("Pitch (semitones)", "pitch_semitones", -24, 24, 0)
        s("Formant shift", "formant_shift", -6, 6, 1)
        s("Clarity %", "clarity", 0, 100, 2, 0)
        s("Warmth %", "warmth", 0, 100, 3, 0)
        s("Reverb room", "reverb_room", 0, 1, 4)
        s("Reverb damping", "reverb_damping", 0, 1, 5)
        s("Reverb wet", "reverb_wet", 0, 1, 6)
        s("Echo delay (ms)", "echo_delay_ms", 0, 1000, 7, 0)
        s("Echo feedback", "echo_feedback", 0, 1, 8)
        s("Echo wet", "echo_wet", 0, 1, 9)
        s("De-esser freq (Hz)", "deesser_freq", 3000, 12000, 10, 0)
        s("De-esser threshold (off=-80)", "deesser_threshold_db", -80, -6, 11)
        s("Gate threshold", "gate_threshold_db", -80, -20, 12)
        s("Gate attack (ms)", "gate_attack_ms", 1, 100, 13)
        s("Gate release (ms)", "gate_release_ms", 10, 500, 14)
        s("Vibrato rate (Hz)", "vibrato_rate_hz", 1, 12, 15)
        s("Vibrato depth", "vibrato_depth", 0, 1, 16)

    def _build_enhance_tab(self, tab):
        enh = self.params.enhance
        row = 0

        def toggle_enabled():
            enh.enabled = not enh.enabled
            btn.configure(text="Enabled ✓" if enh.enabled else "Disabled")
            self.on_change()

        btn = ctk.CTkButton(
            tab, text="Enabled ✓" if enh.enabled else "Disabled",
            command=toggle_enabled
        )
        btn.grid(row=row, column=0, columnspan=3, pady=8)
        row += 1

        def s(label, attr, from_, to, r, decimals=0):
            sl = _slider(tab, label, from_, to, getattr(enh, attr),
                         lambda v, a=attr: (setattr(enh, a, float(v)), self.on_change()),
                         r, decimals)
            self._sliders[f"enhance.{attr}"] = sl

        s("Noise suppression %", "noise_suppression", 0, 100, row)
        row += 1
        s("Voice restoration %", "voice_restoration", 0, 100, row)
        row += 1

        ctk.CTkLabel(
            tab, text="Broadcast Presets", font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, columnspan=3, pady=(12, 4))
        row += 1

        presets = {
            "Podcast": (55.0, 70.0),
            "Radio": (80.0, 85.0),
            "Assistant": (90.0, 90.0),
            "Reel": (45.0, 55.0),
        }
        frame = ctk.CTkFrame(tab, fg_color="transparent")
        frame.grid(row=row, column=0, columnspan=3)
        for name, (ns, vr) in presets.items():
            def apply_preset(n=ns, v=vr):
                enh.noise_suppression = n
                enh.voice_restoration = v
                self._sliders["enhance.noise_suppression"].set(n)
                self._sliders["enhance.voice_restoration"].set(v)
                self.on_change()
            ctk.CTkButton(frame, text=name, width=90, command=apply_preset).pack(
                side="left", padx=4
            )

    def _build_rvc_tab(self, tab):
        rvc = self.params.rvc
        row = 0

        def toggle_enabled():
            rvc.enabled = not rvc.enabled
            btn.configure(text="RVC Enabled ✓" if rvc.enabled else "RVC Disabled")
            self.on_change()

        btn = ctk.CTkButton(
            tab,
            text="RVC Enabled ✓" if rvc.enabled else "RVC Disabled",
            command=toggle_enabled
        )
        btn.grid(row=row, column=0, columnspan=3, pady=8)
        row += 1

        ctk.CTkLabel(tab, text="Voice model (.pth):", anchor="w").grid(
            row=row, column=0, sticky="w", padx=8)
        self._model_var = ctk.StringVar(value=rvc.model_path or "No model loaded")
        ctk.CTkLabel(tab, textvariable=self._model_var, anchor="w", wraplength=220).grid(
            row=row, column=1, sticky="w")

        def browse_model():
            from tkinter import filedialog
            path = filedialog.askopenfilename(filetypes=[("PyTorch model", "*.pth")])
            if path:
                rvc.model_path = path
                self._model_var.set(path.split("/")[-1].split("\\")[-1])

        ctk.CTkButton(tab, text="Browse", width=80, command=browse_model).grid(
            row=row, column=2, padx=4)
        row += 1

        ctk.CTkLabel(tab, text="Index file (.index):", anchor="w").grid(
            row=row, column=0, sticky="w", padx=8)
        self._index_var = ctk.StringVar(value=rvc.index_path or "Optional")

        def browse_index():
            from tkinter import filedialog
            path = filedialog.askopenfilename(filetypes=[("RVC index", "*.index")])
            if path:
                rvc.index_path = path
                self._index_var.set(path.split("/")[-1].split("\\")[-1])

        ctk.CTkLabel(tab, textvariable=self._index_var, anchor="w").grid(
            row=row, column=1, sticky="w")
        ctk.CTkButton(tab, text="Browse", width=80, command=browse_index).grid(
            row=row, column=2, padx=4)
        row += 1

        def s(label, attr, from_, to, r, decimals=2):
            sl = _slider(tab, label, from_, to, getattr(rvc, attr),
                         lambda v, a=attr: (setattr(rvc, a, float(v)), self.on_change()),
                         r, decimals)
            self._sliders[f"rvc.{attr}"] = sl

        s("Pitch offset", "pitch_offset", -12, 12, row, 1)
        row += 1
        s("Index rate", "index_rate", 0, 1, row)
        row += 1
        s("RMS mix rate", "rms_mix_rate", 0, 1, row)
        row += 1
        s("Protect rate", "protect_rate", 0, 0.5, row)
        row += 1

        ctk.CTkLabel(tab, text="Filter radius", anchor="w").grid(
            row=row, column=0, sticky="w", padx=8)
        fr_var = tk.IntVar(value=rvc.filter_radius)
        ctk.CTkSlider(
            tab, from_=0, to=7, number_of_steps=7,
            variable=fr_var,
            command=lambda v: (setattr(rvc, "filter_radius", int(v)), self.on_change())
        ).grid(row=row, column=1, padx=8)
        ctk.CTkLabel(tab, textvariable=fr_var, width=30).grid(row=row, column=2)
        row += 1

        ctk.CTkLabel(tab, text="F0 method", anchor="w").grid(
            row=row, column=0, sticky="w", padx=8)
        f0_var = ctk.StringVar(value=rvc.f0_method)
        ctk.CTkSegmentedButton(
            tab, values=["harvest", "crepe", "rmvpe"],
            variable=f0_var,
            command=lambda v: (setattr(rvc, "f0_method", v), self.on_change())
        ).grid(row=row, column=1, columnspan=2, padx=8, pady=4)

    def load_params(self, params: VoiceParams):
        self.params = params
        # Rebuild tabs with new params so lambdas capture fresh references
        for widget in self.tab_view.winfo_children():
            widget.destroy()
        self._sliders = {}
        self.tab_view.add("DSP Effects")
        self.tab_view.add("AI Enhancement")
        self.tab_view.add("AI Voice (RVC)")
        self._build_dsp_tab(self.tab_view.tab("DSP Effects"))
        self._build_enhance_tab(self.tab_view.tab("AI Enhancement"))
        self._build_rvc_tab(self.tab_view.tab("AI Voice (RVC)"))
