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

## Bundled: FFmpeg (via the `imageio-ffmpeg` wheel)

- **What it's for**: `engines/export_engine.py`'s DSP filter chain (noise
  gate, de-esser, compressor+EQ, reverb/echo, loudnorm) shells out to
  `ffmpeg -af ...`. Previously this called a bare `ffmpeg` on PATH, which
  broke CI (`windows-latest` has no ffmpeg installed) and would equally
  break export for any end user who doesn't have ffmpeg installed — WAV
  export (the final file write) never used ffmpeg, only this DSP step did.
- **Fix (2026-10-01)**: `imageio-ffmpeg` (pinned in `requirements.txt`)
  bundles a complete, real ffmpeg binary as package data
  (`imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe`, ~87.6 MB).
  `export_engine._resolve_ffmpeg_binary()` calls
  `imageio_ffmpeg.get_ffmpeg_exe()`, which resolves (in order) an
  `IMAGEIO_FFMPEG_EXE` env override, this bundled binary, a conda-installed
  ffmpeg, or a system `ffmpeg` on PATH — falling back to the bare string
  `"ffmpeg"` only if `imageio_ffmpeg` itself is unavailable. `build.py`
  collects it into the release exe via `--collect-data=imageio_ffmpeg`
  (preserves the package-relative layout `importlib.resources` needs).
- **Version / provenance**: `imageio-ffmpeg==0.6.0`'s Windows x86_64 binary,
  built by gyan.dev (`ffmpeg version 7.1-essentials_build-www.gyan.dev`).
- **License**: the `imageio-ffmpeg` Python wrapper itself is BSD-2-Clause.
  The bundled ffmpeg *binary* is a separate build with its own license —
  confirmed via `ffmpeg -version`'s configuration string, which includes
  `--enable-gpl --enable-version3` (plus `--enable-libx264`,
  `--enable-libmp3lame`, and other GPL-only components) — i.e. it's a
  **GPLv3** build, not LGPL. The GPLv3 text is identical to the one already
  in this repo's own `LICENSE` (VoiceForge is itself GPL-3.0-or-later), so
  no separate license file is duplicated here; the written source offer is
  FFmpeg's own public source (<https://ffmpeg.org/download.html>) and
  gyan.dev's build scripts (<https://github.com/GyanD/codexffmpeg>) for this
  specific build.
- **License compliance**: ffmpeg is invoked as a separate executable via
  `subprocess` (never linked into the VoiceForge Python process), and
  VoiceForge is itself GPL-3.0-or-later — compatible either as "mere
  aggregation" or under direct compatibility.

## Other direct dependencies (see `requirements.txt` for exact pins)

| Package | License |
|---|---|
| sounddevice | MIT |
| soundfile | BSD-3-Clause |
| numpy | BSD-3-Clause |
| pyrubberband (the Python wrapper, not the CLI binary) | ISC |
| customtkinter | MIT |
| imageio-ffmpeg (Python wrapper; see the bundled-FFmpeg section above for the binary's own license) | BSD-2-Clause |
| deepfilternet | MIT |
