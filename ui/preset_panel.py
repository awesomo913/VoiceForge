from collections.abc import Callable

import customtkinter as ctk

from params import VoiceParams
from presets.manager import CATEGORIES, PresetManager


class PresetPanel(ctk.CTkFrame):
    def __init__(self, parent, preset_manager: PresetManager,
                 on_load: Callable, on_save: Callable, **kwargs):
        super().__init__(parent, **kwargs)
        self.mgr = preset_manager
        self.on_load = on_load
        self.on_save = on_save
        self._selected_name = None
        self._selected_cat = None
        self._build()
        self.refresh()

    def _build(self):
        ctk.CTkLabel(
            self, text="PRESETS", font=ctk.CTkFont(weight="bold", size=13)
        ).pack(pady=(8, 4))

        self.tab_view = ctk.CTkTabview(self, width=260)
        self.tab_view.pack(fill="both", expand=True, padx=4)
        for cat in CATEGORIES:
            self.tab_view.add(cat)

        self._list_frames = {}
        self._list_buttons = {}
        for cat in CATEGORIES:
            frame = ctk.CTkScrollableFrame(self.tab_view.tab(cat))
            frame.pack(fill="both", expand=True)
            self._list_frames[cat] = frame
            self._list_buttons[cat] = []

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=4, pady=4)

        ctk.CTkButton(
            btn_frame, text="Load", width=70, fg_color="#27ae60",
            command=self._do_load
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_frame, text="Save", width=70, fg_color="#2980b9",
            command=self._do_save
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_frame, text="Delete", width=70, fg_color="#c0392b",
            command=self._do_delete
        ).pack(side="left", padx=2)

        io_frame = ctk.CTkFrame(self, fg_color="transparent")
        io_frame.pack(fill="x", padx=4, pady=(0, 4))
        ctk.CTkButton(io_frame, text="Import", width=105, command=self._do_import).pack(
            side="left", padx=2)
        ctk.CTkButton(io_frame, text="Export", width=105, command=self._do_export).pack(
            side="left", padx=2)

    def refresh(self):
        listing = self.mgr.list_presets()
        for cat in CATEGORIES:
            for btn in self._list_buttons[cat]:
                btn.destroy()
            self._list_buttons[cat] = []
            for name in listing.get(cat, []):
                btn = ctk.CTkButton(
                    self._list_frames[cat], text=name, anchor="w",
                    fg_color="transparent", hover_color="#2c3e50",
                    command=lambda n=name, c=cat: self._select(n, c)
                )
                btn.pack(fill="x", padx=4, pady=1)
                self._list_buttons[cat].append(btn)

    def _select(self, name: str, category: str):
        self._selected_name = name
        self._selected_cat = category

    def _do_load(self):
        if not self._selected_name:
            return
        try:
            params = self.mgr.load(self._selected_name, self._selected_cat)
            self.on_load(params)
        except Exception as e:
            import logging
            logging.error(f"Preset load error: {e}")

    def _do_save(self):
        dialog = ctk.CTkInputDialog(text="Preset name:", title="Save Preset")
        name = dialog.get_input()
        if not name:
            return
        cat = self.tab_view.get()
        self.on_save(name, cat)
        self.refresh()

    def _do_delete(self):
        if not self._selected_name or not self._selected_cat:
            return
        self.mgr.delete(self._selected_name, self._selected_cat)
        self._selected_name = None
        self._selected_cat = None
        self.refresh()

    def _do_import(self):
        import json
        import os
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("Preset JSON", "*.json")])
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            name = data.get("name", os.path.basename(path)[:-5])
            cat = data.get("category", "My Voices")
            params = VoiceParams.from_dict(data.get("params", data))
            self.mgr.save(name, cat, params)
            self.refresh()
        except Exception as e:
            import logging
            logging.error(f"Import failed: {e}")

    def _do_export(self):
        if not self._selected_name:
            return
        import json
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Preset JSON", "*.json")],
            initialfile=f"{self._selected_name}.json"
        )
        if not path:
            return
        try:
            params = self.mgr.load(self._selected_name, self._selected_cat)
            with open(path, "w") as f:
                json.dump({
                    "name": self._selected_name,
                    "category": self._selected_cat,
                    "params": params.to_dict()
                }, f, indent=2)
        except Exception as e:
            import logging
            logging.error(f"Export failed: {e}")
