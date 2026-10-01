"""Build VoiceForge.exe — a standalone Windows executable.

Builds with whatever interpreter runs this script. Point it at a dedicated
clean venv so the bundle doesn't drag unrelated packages from a shared
environment:

    .venv\\Scripts\\python.exe build.py

Output: dist\\VoiceForge.exe only (no copies elsewhere — CI picks it up from
dist\\ for releases; a local install is the user's own choice).

Notes:
- Built-in presets (presets/builtin/*.json) are bundled as data files.
- AI noise-suppression (DeepFilterNet, effects/ai_enhance_layer.py) ships its
  model weights from assets/deepfilternet3/ (see THIRD_PARTY.md for the
  upstream source URL, version, and checksum of what's bundled) — no
  first-run download needed. If torch/the model somehow fails to load
  anyway, the layer degrades to a pass-through instead of crashing.
- RVC voice conversion (effects/rvc_layer.py) has no Windows-installable
  backend (rvc_python requires fairseq, which has no Windows wheel) — it is
  excluded from the build and the layer already degrades to a pass-through
  at runtime when rvc_python is missing.
- Formant shift (part of DSP pitch/formant shifting) needs the external
  `rubberband` command-line tool, which is GPL-2.0-licensed and is NOT
  downloaded by this script (this project doesn't fetch and execute
  third-party binaries as part of an automated build). If a human has
  manually placed a verified copy at vendor/rubberband/ (see
  THIRD_PARTY.md for the exact steps and the official download page), this
  script bundles it and formant shift works in the built exe. Otherwise the
  build proceeds exactly as before and formant shift keeps using
  pedalboard's pitch-only fallback — see README Limitations.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "VoiceForge"
MAIN = os.path.join(HERE, "main.py")
VENDOR_RUBBERBAND_DIR = os.path.join(HERE, "vendor", "rubberband")

# Filled in once a human has verified a specific downloaded rubberband.exe
# against the official release (see THIRD_PARTY.md) and recorded its sha256
# here. Left as None until that manual step has actually happened — an
# unpinned binary is bundled with a loud warning rather than silently trusted.
VENDOR_RUBBERBAND_SHA256: str | None = None

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
    ("assets/deepfilternet3", "assets/deepfilternet3"),
]


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_vendored_rubberband_binaries() -> list[str]:
    """Return every file under vendor/rubberband/ to bundle, verifying the
    main executable's checksum when VENDOR_RUBBERBAND_SHA256 is pinned.

    Returns an empty list (and prints why) when nothing is vendored — this is
    the expected/default state until a human completes the manual steps in
    THIRD_PARTY.md. Never downloads anything itself.
    """
    if not os.path.isdir(VENDOR_RUBBERBAND_DIR):
        print(
            "[build] vendor/rubberband/ not found — building without the rubberband "
            "CLI. Formant shift will use pedalboard's pitch-only fallback in this "
            "build. See THIRD_PARTY.md to vendor it."
        )
        return []

    files = sorted(
        os.path.join(VENDOR_RUBBERBAND_DIR, name)
        for name in os.listdir(VENDOR_RUBBERBAND_DIR)
        if os.path.isfile(os.path.join(VENDOR_RUBBERBAND_DIR, name))
    )
    exe_path = os.path.join(VENDOR_RUBBERBAND_DIR, "rubberband.exe")
    if not files or not os.path.isfile(exe_path):
        print(
            f"[build] {VENDOR_RUBBERBAND_DIR} exists but has no rubberband.exe in it — "
            "ignoring it and building without the rubberband CLI."
        )
        return []

    actual_hash = _sha256(exe_path)
    if VENDOR_RUBBERBAND_SHA256 is None:
        print(
            f"[build] WARNING: bundling vendor/rubberband/rubberband.exe with NO pinned "
            f"checksum to verify against (VENDOR_RUBBERBAND_SHA256 is None in build.py). "
            f"Its actual sha256 is {actual_hash} — verify this against the official "
            f"download (see THIRD_PARTY.md) and pin it in build.py before shipping a "
            f"release build."
        )
    elif actual_hash != VENDOR_RUBBERBAND_SHA256:
        raise SystemExit(
            f"[build] FAILED: vendor/rubberband/rubberband.exe sha256 {actual_hash} "
            f"does not match the pinned VENDOR_RUBBERBAND_SHA256 "
            f"({VENDOR_RUBBERBAND_SHA256}) in build.py — refusing to bundle a binary "
            f"that doesn't match what was verified. Re-download from the official "
            f"source in THIRD_PARTY.md if this wasn't intentional."
        )
    else:
        print(f"[build] vendor/rubberband/rubberband.exe sha256 verified: {actual_hash}")

    return files


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
    for binary_path in _find_vendored_rubberband_binaries():
        args.append(f"--add-binary={binary_path}{sep}vendor/rubberband")
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
