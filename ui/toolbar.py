import customtkinter as ctk


class Toolbar(ctk.CTkFrame):
    def __init__(self, parent, on_record, on_stop, on_preview, on_export, **kwargs):
        super().__init__(parent, **kwargs)
        self._on_record = on_record
        self._on_stop = on_stop
        self._on_preview = on_preview
        self._on_export = on_export
        self._recording = False
        self._elapsed = 0
        self._timer_id = None
        self._build()

    def _build(self):
        btn_cfg = {"width": 120, "height": 36, "corner_radius": 6}

        self.btn_record = ctk.CTkButton(
            self, text="● REC", fg_color="#c0392b", hover_color="#e74c3c",
            command=self._on_record, **btn_cfg
        )
        self.btn_record.pack(side="left", padx=(8, 4), pady=6)

        self.btn_stop = ctk.CTkButton(
            self, text="■ STOP", fg_color="#7f8c8d", hover_color="#95a5a6",
            command=self._on_stop, **btn_cfg
        )
        self.btn_stop.pack(side="left", padx=4, pady=6)

        self.btn_preview = ctk.CTkButton(
            self, text="▶ PREVIEW", fg_color="#27ae60", hover_color="#2ecc71",
            command=self._on_preview, **btn_cfg
        )
        self.btn_preview.pack(side="left", padx=4, pady=6)

        self.btn_export = ctk.CTkButton(
            self, text="⬇ EXPORT WAV", fg_color="#2980b9", hover_color="#3498db",
            command=self._on_export, **btn_cfg
        )
        self.btn_export.pack(side="left", padx=4, pady=6)

        self.lbl_message = ctk.CTkLabel(self, text="", text_color="#95a5a6")
        self.lbl_message.pack(side="left", padx=12)

        self.lbl_timer = ctk.CTkLabel(
            self, text="00:00", font=ctk.CTkFont(family="Courier", size=14)
        )
        self.lbl_timer.pack(side="right", padx=12)

    def set_recording(self, is_recording: bool):
        self._recording = is_recording
        if is_recording:
            self.btn_record.configure(fg_color="#e74c3c")
            self._elapsed = 0
            self._tick()
        else:
            if self._timer_id:
                self.after_cancel(self._timer_id)
                self._timer_id = None
            self.btn_record.configure(fg_color="#c0392b")

    def _tick(self):
        if self._recording:
            mins, secs = divmod(self._elapsed, 60)
            self.lbl_timer.configure(text=f"{mins:02d}:{secs:02d}")
            self._elapsed += 1
            self._timer_id = self.after(1000, self._tick)

    def show_message(self, msg: str):
        self.lbl_message.configure(text=msg)
        self.after(4000, lambda: self.lbl_message.configure(text=""))
