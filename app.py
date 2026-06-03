import json
import os
import logging
import customtkinter as ctk
from params import VoiceParams
from recorder import Recorder, get_input_devices
from engines.preview_engine import PreviewEngine
from engines.export_engine import ExportEngine
from presets.manager import PresetManager

# from ui.toolbar import Toolbar        # Task 13
# from ui.waveform import WaveformWidget  # Task 14
# from ui.effects_panel import EffectsPanel  # Task 15
# from ui.preset_panel import PresetPanel    # Task 16

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
        # UI panels wired in Tasks 13-16
        # Stubs so the app shell is importable now
        self.toolbar = None
        self.waveform = None
        self.effects_panel = None
        self.preset_panel = None
        logging.info("DECISION UI panels not yet wired (Tasks 13-16 pending)")

    def _on_record(self):
        self.recorder.start()
        if self.toolbar is not None:
            self.toolbar.set_recording(True)
        logging.info("STATE ready→recording")

    def _on_stop(self):
        audio = self.recorder.stop()
        if self.toolbar is not None:
            self.toolbar.set_recording(False)
        if audio is not None:
            self._raw_audio = audio
            self._sample_rate = self.recorder.sample_rate
            if self.waveform is not None:
                self.waveform.draw(audio)
            logging.info(f"STATE recording→ready samples={len(audio)}")

    def _on_preview(self):
        if self._raw_audio is None:
            if self.toolbar is not None:
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
            if self.toolbar is not None:
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
            if self.toolbar is not None:
                self.toolbar.show_message(f"Exported: {os.path.basename(path)}")
            logging.info(f"STATE ready export_done={path}")
        except Exception as exc:
            logging.error(f"Export failed: {exc}")
            if self.toolbar is not None:
                self.toolbar.show_message(f"Export failed: {exc}")

    def _on_params_change(self):
        pass  # params object mutated in-place by EffectsPanel

    def _on_preset_load(self, params: VoiceParams):
        self.params = params
        if self.effects_panel is not None:
            self.effects_panel.load_params(params)

    def _on_preset_save(self, name: str, category: str):
        self.preset_manager.save(name, category, self.params)
        if self.preset_panel is not None:
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
