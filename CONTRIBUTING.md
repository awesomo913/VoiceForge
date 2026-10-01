# Contributing to VoiceForge

Thanks for considering a contribution. VoiceForge is a small, free, open-source offline voice-effects studio — issues and PRs of any size are welcome.

## License

VoiceForge is licensed [GPL-3.0-or-later](LICENSE). By submitting a contribution, you agree it's licensed under the same terms (GPL-3.0-or-later) so it can be distributed as part of the project. See [THIRD_PARTY.md](THIRD_PARTY.md) for the licenses of bundled/vendored third-party components.

## Dev setup

Requires Python 3.11.

```bash
git clone https://github.com/awesomo913/VoiceForge.git
cd VoiceForge
uv venv --python 3.11
uv pip install -r requirements.txt
python main.py
```

For running the full check suite and building the exe, also install the dev dependencies:

```bash
uv pip install -r requirements-dev.txt
```

`pyrubberband` (used for pitch/formant shifting) shells out to the `rubberband` command-line binary. `build.py` fetches and checksum-verifies a pinned release into `vendor/rubberband/` automatically (see [vendor/README.md](vendor/README.md)) when building the exe, but running from source via `python main.py` doesn't go through `build.py` — if `rubberband` isn't on `PATH` and `vendor/rubberband/` isn't populated, the DSP layer automatically falls back to `pedalboard`'s built-in pitch shifter (formant shifting is unavailable in that fallback — see `effects/dsp_layer.py::_apply_pitch_formant`). Run `python -c "import build; build.fetch_vendor_rubberband()"` once if you want it available from source too.

## Running tests and lint

```bash
pytest
ruff check .
```

Please run both before opening a PR. Tests never open the GUI window, record from a real microphone, play audio out loud, or require a GPU/DeepFilterNet model download — recording, playback, and the AI layers are mocked.

## Architecture

VoiceForge processes audio through three layers, always in this order (see `engines/preview_engine.py` and `engines/export_engine.py`):

1. **DSP** (`effects/dsp_layer.py`) — pitch/formant shift, vibrato, noise gate, de-esser, clarity (compression + EQ), warmth, reverb, echo. Pure signal processing, always available.
2. **AI noise suppression** (`effects/ai_enhance_layer.py`) — DeepFilterNet. Degrades gracefully: if the model or its `torch` backend can't load, the layer logs the failure and passes audio through unchanged instead of crashing.
3. **AI voice conversion / RVC** (`effects/rvc_layer.py`) — only runs if the user has enabled it and pointed it at their own `.pth` model file. `rvc_python` has no installable Windows wheel (its `fairseq` dependency doesn't build there), so on Windows this layer always passes audio through unchanged. See [SECURITY.md](SECURITY.md) and the README for the voice-cloning ethics notes.

Other key files:

- `params.py` — `VoiceParams` dataclass tree (DSP/enhance/RVC settings), JSON round-trip.
- `presets/manager.py` — loads/saves named presets under `presets/builtin/` (shipped, read-only) and `presets/user/` (yours, gitignored).
- `recorder.py` — microphone capture via `sounddevice`.
- `ui/` — CustomTkinter widgets (toolbar, waveform, effects panel, preset panel). UI code should stay a thin layer over `params.py`/`engines/` — it should not contain DSP or file-format logic.

### Preset naming

Built-in preset names (`presets/builtin/*.json`) must stay generic — no celebrity names, no third-party trademarked product names (a prior version shipped presets named after well-known voice assistants; they were renamed). `tests/test_preset_manager.py::test_no_trademarked_names_in_builtin_presets` guards against regressions on a short list of known terms, but use judgment for anything not on that list.

## Code style

- Small, focused functions over large ones; prefer early returns over deep nesting.
- No silent `except:` blocks — catch specific exceptions, log or surface them, never swallow.
- Anything that touches the GUI (tkinter/customtkinter) must run on the main thread; background threads (recording, preview processing) hand results back without touching widgets directly from the thread.
- Use `logging` (module-level `logger = logging.getLogger(__name__)` or `logging.getLogger(__name__)`), not `print()`, in library code.

## Pull request checklist

- [ ] `pytest` passes
- [ ] `ruff check .` passes with no new warnings
- [ ] No new silent exception handling
- [ ] No celebrity/trademarked names added to presets or UI text
- [ ] Updated `CHANGELOG.md` under `[Unreleased]` if the change is user-facing
- [ ] Description explains *why*, not just *what*
