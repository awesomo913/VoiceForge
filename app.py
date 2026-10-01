import json
import logging
import os
import pathlib
import threading
from tkinter import TclError

import customtkinter as ctk

from engines.export_engine import ExportEngine
from engines.preview_engine import PreviewEngine
from params import VoiceParams
from presets.manager import PresetManager
from recorder import Recorder
from ui.effects_panel import EffectsPanel
from ui.preset_panel import PresetPanel
from ui.toolbar import Toolbar
from ui.waveform import WaveformWidget

SESSION_FILE = str(pathlib.Path.home() / ".voiceforge" / "last_session.json")


class _UIStatusHandler(logging.Handler):
    """Surfaces select log records to the toolbar's status label.

    Only records carrying a `ui_status` extra (set via
    `log.warning(..., extra={"ui_status": "..."})`) are forwarded — most log
    output never reaches the UI. Each distinct message is shown at most once
    per run, so a condition that keeps recurring on every preview/export
    (e.g. a missing optional dependency) doesn't spam the status bar.
    """

    def __init__(self, app: "VoiceForgeApp") -> None:
        super().__init__(level=logging.WARNING)
        self._app = app
        self._shown: set[str] = set()

    def emit(self, record: logging.LogRecord) -> None:
        message = getattr(record, "ui_status", None)
        if not message or message in self._shown:
            return
        self._shown.add(message)
        self._app.post_status(message)


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

        self._status_handler = _UIStatusHandler(self)
        logging.getLogger().addHandler(self._status_handler)

        self._load_session()
        self._build_ui()

    def run_on_ui_thread(self, fn) -> None:
        """Schedule fn() to run on the Tk main loop. Safe to call from any thread.

        Background work (preview processing, in particular) must never touch
        Tk widgets directly — Tkinter is not thread-safe. Everything that
        updates a widget from a worker thread goes through here instead.
        """
        try:
            self.root.after(0, fn)
        except (RuntimeError, TclError) as exc:
            # The window was already closed/destroyed by the time the worker
            # thread finished — nothing to update, just note it in the log.
            logging.warning(f"UI update skipped (window gone): {exc}")

    def post_status(self, message: str) -> None:
        """Show *message* in the toolbar status label. Safe from any thread."""
        self.run_on_ui_thread(lambda: self.toolbar.show_message(message))

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
        self.toolbar.show_message("Processing...")

        def _run():
            try:
                processed = self.preview_engine.process_and_play(
                    self._raw_audio, self._sample_rate, self.params
                )
            except Exception as exc:
                logging.error(f"Preview processing failed: {exc}")
                self.post_status(f"Preview failed: {exc}")
                return
            self._processed_audio = processed
            self.post_status("Playing")
            logging.info("STATE previewing→ready")

        threading.Thread(target=_run, daemon=True).start()

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
        pathlib.Path(SESSION_FILE).parent.mkdir(parents=True, exist_ok=True)
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE) as f:
                    self.params = VoiceParams.from_dict(json.load(f))
            except Exception as e:
                logging.warning(f"Could not restore session: {e}")

    def _on_close(self):
        try:
            with open(SESSION_FILE, "w") as f:
                json.dump(self.params.to_dict(), f, indent=2)
        except Exception as exc:
            logging.warning(f"Could not save session: {exc}")
        # Without this, a closed window's handler stays on the root logger
        # forever — each later log call would try to schedule a status update
        # on a destroyed Tk root (harmless, caught by run_on_ui_thread, but
        # wasted work that accumulates if more than one instance is ever
        # created in-process, e.g. in tests).
        logging.getLogger().removeHandler(self._status_handler)
        self.root.destroy()
