import sys
import os
from diagnostics_logger import bootstrap

bootstrap("VoiceForge")

import logging
logging.info("STATE init→starting")

import customtkinter as ctk
from app import VoiceForgeApp


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    app = VoiceForgeApp(root)
    logging.info("STATE starting→ready")
    root.mainloop()
    logging.info("STATE ready→shutdown")


if __name__ == "__main__":
    main()
