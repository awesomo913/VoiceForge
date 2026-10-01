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
  `rubberband` command-line tool, which is GPL-2.0-or-later licensed.
  vendor/rubberband/ is gitignored (the binary is never committed), but a
  specific release has been verified (sha256 + Authenticode signature by
  Christopher Cannam / Particular Programs Ltd, the upstream author — see
  THIRD_PARTY.md) and its exact download URL + checksum are pinned below, so
  `fetch_vendor_rubberband()` can reproduce the same vendoring step on a
  clean checkout (CI, or a fresh dev machine) without a human repeating the
  manual verification each time. If vendor/rubberband/rubberband.exe is
  already present locally, nothing is (re-)downloaded. If neither is true
  and fetching isn't requested, the build proceeds exactly as before and
  formant shift keeps using pedalboard's pitch-only fallback — see README
  Limitations.
- Export's FFmpeg DSP filter chain (engines/export_engine.py) uses the real
  ffmpeg binary bundled by the `imageio-ffmpeg` wheel, collected here via
  `--collect-data=imageio_ffmpeg` — no system ffmpeg install is required to
  build or to run the resulting exe. See THIRD_PARTY.md for that binary's
  own license (it's a GPLv3 build).
"""
from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "VoiceForge"
MAIN = os.path.join(HERE, "main.py")
VENDOR_RUBBERBAND_DIR = os.path.join(HERE, "vendor", "rubberband")

# Pinned, verified Rubber Band 4.0.0 Windows CLI release (see THIRD_PARTY.md
# for the full verification record: zip sha256, rubberband.exe sha256, and
# the Authenticode signature chain confirming it's signed by Christopher
# Cannam / Particular Programs Ltd, Rubber Band's own author/publisher).
VENDOR_RUBBERBAND_ZIP_URL = (
    "https://breakfastquay.com/files/releases/"
    "rubberband-4.0.0-gpl-executable-windows.zip"
)
VENDOR_RUBBERBAND_ZIP_SHA256 = (
    "f2d47fc64dbb42f6cc62edf7933ac4fa89d8f0ef8b9cf97b6afc263a7fe05644"
)
# The exact file this build bundles and verifies before every PyInstaller run.
VENDOR_RUBBERBAND_SHA256 = "d26d81e20f48ea33070e638f58bdeb6a61ce7f0946d8f2629f30441caa2905d1"
# Only these files from the release zip are vendored (sndfile.dll is
# libsndfile, LGPL-licensed, required by rubberband.exe at runtime for audio
# file I/O; COPYING.txt is Rubber Band's own GPL-2.0-or-later license text).
_VENDOR_RUBBERBAND_ZIP_MEMBERS = {
    "rubberband-4.0.0-gpl-executable-windows/rubberband.exe": "rubberband.exe",
    "rubberband-4.0.0-gpl-executable-windows/sndfile.dll": "sndfile.dll",
    "rubberband-4.0.0-gpl-executable-windows/COPYING.txt": "COPYING.txt",
}


def fetch_vendor_rubberband(force: bool = False) -> None:
    """Download and verify the pinned Rubber Band release into vendor/rubberband/.

    No-ops if vendor/rubberband/rubberband.exe already exists and *force* is
    False — this is meant to make CI/fresh-checkout builds reproducible, not
    to silently re-fetch over a build environment someone already set up by
    hand. Verifies the zip's sha256 against VENDOR_RUBBERBAND_ZIP_SHA256
    before extracting anything; aborts loudly on a mismatch rather than ever
    trusting an unverified download.
    """
    exe_path = os.path.join(VENDOR_RUBBERBAND_DIR, "rubberband.exe")
    if os.path.isfile(exe_path) and not force:
        print(f"[build] {exe_path} already present — not re-downloading.")
        return

    print(f"[build] Downloading {VENDOR_RUBBERBAND_ZIP_URL} ...")
    with urllib.request.urlopen(VENDOR_RUBBERBAND_ZIP_URL, timeout=120) as resp:
        zip_bytes = resp.read()

    actual_zip_hash = hashlib.sha256(zip_bytes).hexdigest()
    if actual_zip_hash != VENDOR_RUBBERBAND_ZIP_SHA256:
        raise SystemExit(
            f"[build] FAILED: downloaded zip sha256 {actual_zip_hash} does not match "
            f"the pinned VENDOR_RUBBERBAND_ZIP_SHA256 ({VENDOR_RUBBERBAND_ZIP_SHA256}) "
            f"— refusing to extract an unverified download. If the upstream release "
            f"genuinely changed, this pin needs a deliberate, reviewed update, not an "
            f"automatic bypass."
        )
    print(f"[build] Zip sha256 verified: {actual_zip_hash}")

    os.makedirs(VENDOR_RUBBERBAND_DIR, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for member, dest_name in _VENDOR_RUBBERBAND_ZIP_MEMBERS.items():
            with zf.open(member) as src:
                data = src.read()
            with open(os.path.join(VENDOR_RUBBERBAND_DIR, dest_name), "wb") as dst:
                dst.write(data)
            print(f"[build] Extracted {member} -> vendor/rubberband/{dest_name}")

    actual_exe_hash = _sha256(exe_path)
    if actual_exe_hash != VENDOR_RUBBERBAND_SHA256:
        raise SystemExit(
            f"[build] FAILED: extracted rubberband.exe sha256 {actual_exe_hash} does "
            f"not match the pinned VENDOR_RUBBERBAND_SHA256 ({VENDOR_RUBBERBAND_SHA256}) "
            f"— the verified zip's sha256 matched, but the executable inside it didn't "
            f"match what was separately verified (Authenticode-signed by Christopher "
            f"Cannam, see THIRD_PARTY.md). Refusing to use it."
        )
    print(f"[build] vendor/rubberband/rubberband.exe sha256 verified: {actual_exe_hash}")

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
    # The actual ffmpeg.exe imageio-ffmpeg ships as package data under
    # imageio_ffmpeg/binaries/ — collecting it preserves the package-relative
    # layout that imageio_ffmpeg.get_ffmpeg_exe() (via importlib.resources)
    # needs to find it inside the frozen exe. See engines/export_engine.py.
    "imageio_ffmpeg",
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


def _find_vendored_rubberband_binaries() -> list[tuple[str, str]]:
    """Return (absolute_path, dest_subdir) for every file under
    vendor/rubberband/ to bundle — walked recursively, so a nested support
    folder (e.g. a licenses/ or lib/ subdirectory some CLI tool distributions
    ship with) isn't silently dropped — verifying the main executable's
    checksum when VENDOR_RUBBERBAND_SHA256 is pinned.

    Only rubberband.exe itself is checksum-verified; any other file found
    alongside it (DLLs, data files, ...) is bundled unverified and this is
    printed explicitly for each one rather than left implicit, since a
    tampered/substituted companion file loaded by rubberband.exe at runtime
    would otherwise defeat the point of verifying the exe at all.

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

    entries: list[tuple[str, str]] = []  # (absolute_path, dest_subdir_under_vendor/rubberband)
    for root, _dirs, filenames in os.walk(VENDOR_RUBBERBAND_DIR):
        rel_dir = os.path.relpath(root, VENDOR_RUBBERBAND_DIR)
        dest_subdir = "vendor/rubberband" if rel_dir == "." else f"vendor/rubberband/{rel_dir}"
        for name in sorted(filenames):
            entries.append((os.path.join(root, name), dest_subdir))

    exe_path = os.path.join(VENDOR_RUBBERBAND_DIR, "rubberband.exe")
    if not entries or not os.path.isfile(exe_path):
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

    other_files = [path for path, _dest in entries if path != exe_path]
    if other_files:
        print(
            f"[build] Also bundling {len(other_files)} file(s) alongside rubberband.exe "
            f"with NO individual checksum check (only the exe itself is verified above): "
            + ", ".join(os.path.relpath(p, VENDOR_RUBBERBAND_DIR) for p in other_files)
        )

    return entries


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
    for binary_path, dest_subdir in _find_vendored_rubberband_binaries():
        args.append(f"--add-binary={binary_path}{sep}{dest_subdir}")
    args.append(MAIN)

    print("[build] Running PyInstaller (this may take 1-2 minutes)...")
    # Timeout so a hung PyInstaller fails loudly instead of blocking forever;
    # 20 minutes comfortably covers slow machines / cold caches.
    subprocess.check_call(args, cwd=HERE, timeout=1200)
    print("[build] PyInstaller complete.")


def main() -> None:
    fetch_vendor_rubberband()
    build_exe()

    exe_path = os.path.join(HERE, "dist", f"{APP_NAME}.exe")
    if not os.path.isfile(exe_path):
        raise SystemExit(f"[build] FAILED: expected {exe_path} but it doesn't exist")
    size_mb = round(os.path.getsize(exe_path) / (1024 * 1024), 1)
    print(f"[build] OK -> {exe_path}  ({size_mb} MB)")


if __name__ == "__main__":
    main()
