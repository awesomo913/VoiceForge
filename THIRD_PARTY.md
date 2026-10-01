# Third-party components

This file documents the significant third-party components VoiceForge bundles
or depends on, their licenses, and — for anything whose weights/binary are
actually shipped inside a release — exactly where they came from and how to
verify them.

## Licensing: VoiceForge is GPL-3.0-or-later

[`pedalboard`](https://github.com/spotify/pedalboard) (Spotify's audio effects
library, used directly as a Python import in `effects/dsp_layer.py` for the
noise gate, de-esser, clarity, warmth, reverb, and echo effects) is licensed
**GPL-3.0**, per its own PyPI classifier (`License :: OSI Approved :: GNU
General Public License v3 (GPLv3)`). Importing a GPL-3.0 library directly
into a program (as opposed to invoking it as a separate process, which is
how `rubberband` below is handled) requires the combined work to also be
distributed under GPL-3.0-compatible terms.

**Resolved 2026-10-01 (owner decision): VoiceForge is relicensed to
GPL-3.0-or-later.** See `LICENSE` for the full text. This also simplifies
the `rubberband` situation below — bundling a GPL-2.0-or-later executable
alongside a GPL-3.0-or-later program is straightforwardly compatible either
way (as a separate process via "mere aggregation", which was already true,
or even if it were linked directly, which it isn't).

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

## Bundled: `rubberband` CLI (Rubber Band Library 4.0.0) + libsndfile

- **What it's for**: `pyrubberband` (used for pitch/formant shifting in
  `effects/dsp_layer.py`) shells out to a `rubberband` command-line
  executable. Without it, formant shift falls back to pedalboard's
  pitch-only shifter (pitch still works; formant shift is silently skipped
  and surfaced once in the UI status bar — see README Limitations). With it
  vendored (the default as of 2026-10-01), formant shift works fully.
- **Version**: Rubber Band 4.0.0, official prebuilt Windows command-line
  release.
- **Source / download**:
  `https://breakfastquay.com/files/releases/rubberband-4.0.0-gpl-executable-windows.zip`
  (official releases page: <https://breakfastquay.com/rubberband/>). Code
  repository: <https://hg.sr.ht/~breakfastquay/rubberband> / GitHub mirror
  <https://github.com/breakfastquay/rubberband> (same version tag).
- **Verification performed before vendoring** (2026-10-01, with the owner's
  explicit authorization to use this specific, already-downloaded file):
  - Zip sha256: `f2d47fc64dbb42f6cc62edf7933ac4fa89d8f0ef8b9cf97b6afc263a7fe05644`
  - `rubberband.exe` sha256: `d26d81e20f48ea33070e638f58bdeb6a61ce7f0946d8f2629f30441caa2905d1`
  - `sndfile.dll` sha256: `4e3bd2de8e1485110eaebef8e1239471f73d608773831c323bf528e05645655e`
  - `rubberband.exe` Authenticode signature: **Valid**, signed by
    `CN=Christopher Cannam, O=Particular Programs Ltd, L=London, C=GB`
    (issued by Certum Code Signing 2021 CA), timestamped through 2034 — this
    is Rubber Band's own author/publisher, independently confirmed via
    `Get-AuthenticodeSignature` against the actual binary, not just trusted
    on the strength of the download URL.
  - Both checksums and the download URL are pinned in `build.py`
    (`VENDOR_RUBBERBAND_ZIP_URL`, `VENDOR_RUBBERBAND_ZIP_SHA256`,
    `VENDOR_RUBBERBAND_SHA256`) and verified again on every build — a
    mismatch aborts the build rather than bundling an unverified file.
- **What's vendored**: only `rubberband.exe`, `sndfile.dll`, and
  `COPYING.txt` from the release zip (not `rubberband-r3.exe`,
  `CHANGELOG.txt`, or `README.txt`, which aren't needed at runtime). Lives at
  `vendor/rubberband/` (gitignored — never committed; `build.py`'s
  `fetch_vendor_rubberband()` reproduces it from the pinned URL + checksums
  on a clean checkout, e.g. in CI).
- **Licenses**:
  - Rubber Band Library and the command-line tool: **GPL-2.0-or-later**
    (see `licenses/rubberband-COPYING`, copied verbatim from this release).
  - `sndfile.dll` (libsndfile, required by `rubberband.exe` for audio file
    I/O): **LGPL** (GNU Lesser General Public License). Source:
    <http://www.mega-nerd.com/libsndfile/> (per Rubber Band's own README) /
    current project home <https://github.com/libsndfile/libsndfile>.
    libsndfile is used here unmodified, as a separate DLL invoked by the
    separately-vendored `rubberband.exe` — VoiceForge's own code never links
    against it directly.
- **License compliance**: Rubber Band is invoked as a separate executable
  via `subprocess` (never linked into the VoiceForge Python process), and
  VoiceForge is itself GPL-3.0-or-later (see above) — both the "mere
  aggregation" reading and a direct compatibility reading are satisfied.
  Required and present: `licenses/rubberband-COPYING` (full GPL-2.0-or-later
  text) and this section as the written source offer for Rubber Band's own
  source code.

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
