"""Build VoiceForge.exe — a standalone Windows executable.

Builds with whatever interpreter runs this script. Point it at a dedicated
clean venv so the bundle doesn't drag unrelated packages from a shared
environment:

    .venv\\Scripts\\python.exe build.py

Output: dist\\VoiceForge.exe only (no copies elsewhere — CI picks it up from
dist\\ for releases; a local install is the user's own choice).

Notes:
- Built-in presets (presets/builtin/*.json) are bundled as data files.
- RVC voice conversion (effects/rvc_layer.py) has no Windows-installable
  backend (rvc_python requires fairseq, which has no Windows wheel) — it is
  excluded from the build and the layer already degrades to a pass-through
  at runtime when rvc_python is missing.
- AI noise-suppression (DeepFilterNet, effects/ai_enhance_layer.py) is
  included when installed. If its torch backend isn't present in the build
  venv, the layer degrades the same way: it logs the failure and passes
  audio through unprocessed rather than crashing.
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "VoiceForge"
MAIN = os.path.join(HERE, "main.py")

# Hidden imports that PyInstaller's static import-analysis misses.
_HIDDEN_IMPORTS = [
    "sounddevice",
    "soundfile",
    "pedalboard",
    "pyrubberband",
    "df",
]

_COLLECT_DATA = [
    # customtkinter's theme JSON assets are not picked up by default.
    "customtkinter",
    # DeepFilterNet's bundled model weights (only present if installed).
    "df",
]

_COLLECT_SUBMODULES = [
    "customtkinter",
]

# rvc_python has no Windows-installable backend (see module docstring) — make
# sure PyInstaller never tries to pull it in even if it's present on PATH.
_EXCLUDE_MODULES = [
    "rvc_python",
]

_ADD_DATA = [
    ("presets/builtin", "presets/builtin"),
]


def build_exe() -> None:
    args = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onefile", "--windowed",
        f"--name={APP_NAME}",
        "--icon", os.path.join(HERE, "assets", "icon.ico"),
    ]
    for mod in _HIDDEN_IMPORTS:
        args.append(f"--hidden-import={mod}")
    for pkg in _COLLECT_DATA:
        args.append(f"--collect-data={pkg}")
    for pkg in _COLLECT_SUBMODULES:
        args.append(f"--collect-submodules={pkg}")
    for mod in _EXCLUDE_MODULES:
        args.append(f"--exclude-module={mod}")
    sep = ";" if os.name == "nt" else ":"
    for src, dest in _ADD_DATA:
        args.append(f"--add-data={src}{sep}{dest}")
    args.append(MAIN)

    print("[build] Running PyInstaller (this may take 1-2 minutes)...")
    # Timeout so a hung PyInstaller fails loudly instead of blocking forever;
    # 20 minutes comfortably covers slow machines / cold caches.
    subprocess.check_call(args, cwd=HERE, timeout=1200)
    print("[build] PyInstaller complete.")


def main() -> None:
    build_exe()

    exe_path = os.path.join(HERE, "dist", f"{APP_NAME}.exe")
    if not os.path.isfile(exe_path):
        raise SystemExit(f"[build] FAILED: expected {exe_path} but it doesn't exist")
    size_mb = round(os.path.getsize(exe_path) / (1024 * 1024), 1)
    print(f"[build] OK -> {exe_path}  ({size_mb} MB)")


if __name__ == "__main__":
    main()
