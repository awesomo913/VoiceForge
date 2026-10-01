from diagnostics_logger import bootstrap

bootstrap("VoiceForge")  # must run before importing anything else so crashes during
# import itself are still captured by the diagnostics logger.

import logging  # noqa: E402

logging.info("STATE init→starting")

import customtkinter as ctk  # noqa: E402

from app import VoiceForgeApp  # noqa: E402


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    VoiceForgeApp(root)
    logging.info("STATE starting→ready")
    root.mainloop()
    logging.info("STATE ready→shutdown")


if __name__ == "__main__":
    main()
