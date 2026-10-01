# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-01

### Added

- Desktop voice-effects studio built with CustomTkinter: record from your microphone or load a clip, apply DSP and AI effects, preview, and export a 24-bit WAV.
- DSP layer (`effects/dsp_layer.py`): pitch shift, formant shift, vibrato, noise gate, de-esser, clarity (compression + presence EQ), warmth (low-shelf), reverb, and echo/delay, via `pedalboard` and `pyrubberband`.
- AI noise suppression and voice restoration via [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) (`effects/ai_enhance_layer.py`), with a graceful pass-through fallback if the model can't load.
- Optional AI voice conversion (RVC) layer (`effects/rvc_layer.py`) — always off by default, only runs when you enable it and supply your own `.pth`/`.index` model files. No models are bundled.
- 11 built-in voice presets across four categories (My Voices, Reel Personas, Assistants, Characters), plus save/load/delete/rename/import/export for your own presets.
- Export engine producing a 24-bit, 48 kHz WAV file via an FFmpeg filter chain plus loudness normalization.
- Session auto-save/restore (`~/.voiceforge/last_session.json`).
- Portable single-file `VoiceForge.exe` distributed via GitHub Releases, built by GitHub Actions on tag with an attached `SHA256SUMS.txt`.

### Changed

- AI noise cleanup (DeepFilterNet) is now fully bundled and working out of the box: `torch==2.1.2` and `torchaudio==2.1.2` (CPU-only wheels from PyTorch's own wheel index) are now pinned dependencies, and the ~8.4 MB DeepFilterNet3 model weights ship in `assets/deepfilternet3/` and in the release exe — no first-run download, no missing-dependency no-op. This makes the release exe considerably larger (~165 MB, up from ~39 MB) — see README Limitations. See `THIRD_PARTY.md` for exact versions, source URLs, and checksums.
- `effects/ai_enhance_layer.py::_get_df_model()` now loads from the bundled model directory when present (falling back to DeepFilterNet's own default/download location for a from-source checkout without the bundled assets), and disables DeepFilterNet's own log file (it would otherwise write directly into the tracked `assets/deepfilternet3/` source directory on every run).
- `effects/dsp_layer.py` and `build.py` now support vendoring the optional `rubberband` command-line tool (needed for formant shift) from `vendor/rubberband/` with a verified checksum. **This project does not download that binary itself** — see `vendor/README.md` and `THIRD_PARTY.md` for why (GPL-2.0 licensing, and automated fetching/bundling of third-party executables isn't something this build does) and the manual steps to add it. Without it, formant shift keeps using pedalboard's pitch-only fallback, as before.

### Fixed

- Renamed the "JARVIS-dark" and "Siri-clean" built-in presets to "Assistant Dark" and "Assistant Clean". Those names referenced third-party trademarked voice-assistant products and, as a side effect of containing a hyphen, exposed a real bug: `PresetManager.load()` resolves a built-in preset by re-slugifying its display name and looking for `<slug>.json` on disk, and the old slugs (`jarvis-dark`, `siri-clean`) didn't match the actual filenames (`jarvis_dark.json`, `siri_clean.json`) — loading either preset by name raised `FileNotFoundError` even though the file existed. The new names slug consistently with their filenames. `tests/test_preset_manager.py` now pins every built-in preset's name-to-filename mapping and loadability so this can't silently regress.
- `app.py`'s preview-processing background thread no longer touches Tk widgets directly (`self.toolbar.show_message(...)` from a worker thread is not thread-safe). All UI updates from any thread now go through `VoiceForgeApp.run_on_ui_thread()`/`post_status()`, which marshal onto the Tk main loop via `root.after()`.
- `diagnostics_logger.py`: the log file moved from `~/.claude/session-data/<date>/exe_VoiceForge.log` (a personal AI-dev-tooling path with no meaning for someone who downloaded the release exe) to `%LOCALAPPDATA%\VoiceForge\logs\app.log` (falling back to `~/.local/state/VoiceForge/logs/app.log`, and further to the OS temp dir if even that can't be created). `threading.excepthook` is now installed alongside `sys.excepthook`, so a crash in a background thread (e.g. the preview-processing worker) reaches the log instead of vanishing — a windowed exe has no stderr to catch it otherwise.
- `ui/waveform.py`: drawing the waveform no longer crashes on a 0-length audio array (divide-by-zero computing the downsample step) or a 0-d/scalar array (no `len()`). The downsample/normalize math was extracted into a standalone, directly-testable `_normalize_for_display()` function.
- `effects/dsp_layer.py` / `effects/ai_enhance_layer.py`: when formant shift silently falls back to pitch-only (no `rubberband` binary) or AI noise cleanup can't run (no `torch`), the condition is now surfaced once in the toolbar's status bar (not just logged) via a new `_UIStatusHandler` on the root logger, deduped per distinct message so a recurring condition doesn't spam the status bar on every preview/export.

### Security / Ethics

- README and SECURITY.md now state explicitly that voice conversion (RVC) models are user-supplied only, none are bundled, and `models/` ships empty (only `.gitkeep`) — verified in CI by the test suite's assumptions and by `.gitignore`.
- `THIRD_PARTY.md` added, documenting every bundled/vendored third-party component's license and provenance, and flagging an open licensing question: `pedalboard` (used directly as a library) is GPL-3.0, which the project owner needs to resolve (relicense, swap the library, or seek alternate terms) — see that file for details. This is a pre-existing condition of the dependency choice, not something introduced by this change; it's being surfaced here for the first time.
