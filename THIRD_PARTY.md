# Third-party components

This file documents the significant third-party components VoiceForge bundles
or depends on, their licenses, and — for anything whose weights/binary are
actually shipped inside a release — exactly where they came from and how to
verify them.

## ⚠ Open licensing question: pedalboard is GPL-3.0

[`pedalboard`](https://github.com/spotify/pedalboard) (Spotify's audio effects
library, used directly as a Python import in `effects/dsp_layer.py` for the
noise gate, de-esser, clarity, warmth, reverb, and echo effects) is licensed
**GPL-3.0**, per its own PyPI classifier (`License :: OSI Approved :: GNU
General Public License v3 (GPLv3)`). This was true before this round of
changes — it's flagged here because the LICENSE file in this repo says MIT,
and importing a GPL-3.0 library directly into a program (as opposed to
invoking it as a separate process, which is how `rubberband` below is
handled) is generally understood to require the combined work to also be
distributed under GPL-3.0-compatible terms.

**This needs an explicit decision from the project owner** — options include:
relicensing VoiceForge as GPL-3.0 (or a GPL-3.0-compatible license),
replacing `pedalboard` with a differently-licensed DSP library, or getting
clarity on whether Spotify offers alternate licensing terms. This document
does not resolve it; it surfaces it so it isn't shipped unnoticed.

## Bundled: DeepFilterNet3 model weights

- **What**: `assets/deepfilternet3/config.ini` and
  `assets/deepfilternet3/checkpoints/model_120.ckpt.best` (~8.4 MB total) —
  the pretrained noise-suppression model used by `effects/ai_enhance_layer.py`.
- **Source**: `https://github.com/Rikorose/DeepFilterNet/raw/main/models/DeepFilterNet3.zip`
  — this is the exact URL the `deepfilternet` PyPI package's own `init_df()`
  function downloads from on first use (see `df/enhance.py` /
  `get_model_basedir()` in the installed package). Bundling it here just
  means a release build ships it instead of fetching it on first run.
- **Version**: DeepFilterNet3, checkpoint epoch 120 (`model_120.ckpt.best`),
  downloaded 2026-10-01 against `deepfilternet==0.5.6`.
- **License**: MIT (same as the `deepfilternet` package itself).
- **Checksum** (`sha256sum assets/deepfilternet3/checkpoints/model_120.ckpt.best`):
  `23b92884f63ccf54bb026014604625ab231657b6480df65db4095c4c171e6003`

## Bundled: torch / torchaudio (CPU-only)

- **What**: `torch==2.1.2` and `torchaudio==2.1.2`, installed from PyTorch's
  own CPU wheel index (`https://download.pytorch.org/whl/cpu`) rather than
  the default PyPI wheels, which include CUDA binaries VoiceForge doesn't use.
- **Why pinned to 2.1.2 specifically**: `deepfilternet==0.5.6`'s `df.io`
  module imports `torchaudio.backend.common.AudioMetaData`, which newer
  torchaudio releases (observed broken starting at 2.11+) removed/moved.
  2.1.2 is the newest pair confirmed, by actually running AI noise
  suppression against real audio (not just importing the module), to still
  work with this `deepfilternet` version.
- **License**: BSD-3-Clause (both packages).

## Not bundled (requires a manual step): `rubberband` CLI

- **What it's for**: `pyrubberband` (used for pitch/formant shifting in
  `effects/dsp_layer.py`) shells out to a `rubberband` command-line
  executable. Without it, formant shift falls back to pedalboard's
  pitch-only shifter (pitch still works; formant shift is silently skipped
  and now surfaced once in the UI status bar — see README Limitations).
- **Why it isn't bundled automatically**: Rubber Band's command-line tool is
  **GPL-2.0**-licensed, and more importantly, fetching and embedding a
  third-party compiled executable from a website as part of an automated
  build is not something this project's tooling does — that's a manual,
  human-verified step (download, check whatever signature/checksum the
  publisher provides, confirm it's the real thing) by design, documented in
  `vendor/README.md`.
- **Official source**: <https://breakfastquay.com/rubberband/> (project
  homepage; downloads page links the Windows command-line build).
- **License compliance when it IS vendored**: Rubber Band is invoked as a
  separate executable via `subprocess` (never linked into the Python
  process), which is "mere aggregation" under GPL-2.0 — VoiceForge itself
  doesn't need to be GPL-licensed as a result. What IS required, and is
  included once vendored:
  - `licenses/rubberband-COPYING` — the GPL-2.0 license text (add the exact
    text shipped with whatever release is downloaded).
  - This section of THIRD_PARTY.md as the written source offer: Rubber Band's
    source code is available from the project's own site and from
    <https://github.com/breakfastquay/rubberband> under the same version's tag.
- **Checksum**: none recorded yet — nothing is currently vendored. See
  `vendor/README.md` and `build.py`'s `VENDOR_RUBBERBAND_SHA256` constant.

## Other direct dependencies (see `requirements.txt` for exact pins)

| Package | License |
|---|---|
| sounddevice | MIT |
| soundfile | BSD-3-Clause |
| numpy | BSD-3-Clause |
| pyrubberband (the Python wrapper, not the CLI binary) | ISC |
| customtkinter | MIT |
| ffmpeg-python | MIT |
| deepfilternet | MIT |
