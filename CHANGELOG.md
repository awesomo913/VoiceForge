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

### Fixed

- Renamed the "JARVIS-dark" and "Siri-clean" built-in presets to "Assistant Dark" and "Assistant Clean". Those names referenced third-party trademarked voice-assistant products and, as a side effect of containing a hyphen, exposed a real bug: `PresetManager.load()` resolves a built-in preset by re-slugifying its display name and looking for `<slug>.json` on disk, and the old slugs (`jarvis-dark`, `siri-clean`) didn't match the actual filenames (`jarvis_dark.json`, `siri_clean.json`) — loading either preset by name raised `FileNotFoundError` even though the file existed. The new names slug consistently with their filenames. `tests/test_preset_manager.py` now pins every built-in preset's name-to-filename mapping and loadability so this can't silently regress.

### Security / Ethics

- README and SECURITY.md now state explicitly that voice conversion (RVC) models are user-supplied only, none are bundled, and `models/` ships empty (only `.gitkeep`) — verified in CI by the test suite's assumptions and by `.gitignore`.
