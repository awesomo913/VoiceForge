import json
import os
import logging
import customtkinter as ctk
from params import VoiceParams
from recorder import Recorder, get_input_devices
from engines.preview_engine import PreviewEngine
from engines.export_engine import ExportEngine
from presets.manager import PresetManager

from ui.toolbar import Toolbar
from ui.waveform import WaveformWidget
from ui.effects_panel import EffectsPanel
from ui.preset_panel import PresetPanel

SESSION_FILE = "last_session.json"


class VoiceForgeApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("VoiceForge")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.params = VoiceParams()
        self.recorder = Recorder()
        self.preview_engine = PreviewEngine()
        self.export_engine = ExportEngine()
        self.preset_manager = PresetManager()
        self._raw_audio = None
        self._processed_audio = None
        self._sample_rate = 48000

        self._load_session()
        self._build_ui()

    def _build_ui(self):
        self.toolbar = Toolbar(
            self.root,
            on_record=self._on_record,
            on_stop=self._on_stop,
            on_preview=self._on_preview,
            on_export=self._on_export,
        )
        self.toolbar.pack(fill="x", side="top")

        self.waveform = WaveformWidget(self.root, height=80)
        self.waveform.pack(fill="x", side="top", padx=8, pady=(4, 0))

        center = ctk.CTkFrame(self.root)
        center.pack(fill="both", expand=True, padx=8, pady=8)

        self.effects_panel = EffectsPanel(
            center,
            params=self.params,
            on_change=self._on_params_change,
        )
        self.effects_panel.pack(side="left", fill="both", expand=True)

        self.preset_panel = PresetPanel(
            center,
            preset_manager=self.preset_manager,
            on_load=self._on_preset_load,
            on_save=self._on_preset_save,
        )
        self.preset_panel.pack(side="right", fill="y")
        logging.info("STATE init UI panels wired")

    def _on_record(self):
        self.recorder.start()
        self.toolbar.set_recording(True)
        logging.info("STATE ready→recording")

    def _on_stop(self):
        audio = self.recorder.stop()
        self.toolbar.set_recording(False)
        if audio is not None:
            self._raw_audio = audio
            self._sample_rate = self.recorder.sample_rate
            self.waveform.draw(audio)
            logging.info(f"STATE recording→ready samples={len(audio)}")

    def _on_preview(self):
        if self._raw_audio is None:
            self.toolbar.show_message("Record something first")
            return
        logging.info("STATE ready→previewing")
        processed = self.preview_engine.process_and_play(
            self._raw_audio, self._sample_rate, self.params
        )
        self._processed_audio = processed
        logging.info("STATE previewing→ready")

    def _on_export(self):
        if self._raw_audio is None:
            self.toolbar.show_message("Record something first")
            return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV audio", "*.wav")],
            title="Export WAV",
        )
        if not path:
            return
        logging.info(f"DECISION export path={path}")
        try:
            self.export_engine.export(self._raw_audio, self._sample_rate, self.params, path)
            self.toolbar.show_message(f"Exported: {os.path.basename(path)}")
            logging.info(f"STATE ready export_done={path}")
        except Exception as exc:
            logging.error(f"Export failed: {exc}")
            self.toolbar.show_message(f"Export failed: {exc}")

    def _on_params_change(self):
        pass  # params object mutated in-place by EffectsPanel

    def _on_preset_load(self, params: VoiceParams):
        self.params = params
        self.effects_panel.load_params(params)

    def _on_preset_save(self, name: str, category: str):
        self.preset_manager.save(name, category, self.params)
        self.preset_panel.refresh()

    def _load_session(self):
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r") as f:
                    self.params = VoiceParams.from_dict(json.load(f))
            except Exception as exc:
                logging.warning(f"Could not restore session: {exc}")

    def _on_close(self):
        try:
            with open(SESSION_FILE, "w") as f:
                json.dump(self.params.to_dict(), f, indent=2)
        except Exception as exc:
            logging.warning(f"Could not save session: {exc}")
        self.root.destroy()
