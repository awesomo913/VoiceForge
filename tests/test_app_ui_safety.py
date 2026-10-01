"""Tests for app.py's thread-to-UI marshaling, without ever creating a real
Tk/CustomTkinter window (VoiceForgeApp.__init__ builds a full GUI and must
never run in tests/CI). VoiceForgeApp.run_on_ui_thread / post_status and
_UIStatusHandler only touch `self.root` / `self.toolbar` / `self._app`, so
they're exercised here against small duck-typed stand-ins instead.
"""

import logging
from tkinter import TclError
from unittest.mock import MagicMock

import app as app_module
from app import VoiceForgeApp, _UIStatusHandler


class _FakeRoot:
    """Stands in for a Tk root. `after(0, fn)` just records fn instead of
    scheduling it on a real event loop."""

    def __init__(self, raise_on_after: Exception | None = None):
        self.scheduled = []
        self._raise_on_after = raise_on_after
        self.destroy = MagicMock()

    def after(self, delay, fn):
        if self._raise_on_after is not None:
            raise self._raise_on_after
        self.scheduled.append(fn)


class _FakeApp:
    """Minimal stand-in exposing exactly what run_on_ui_thread/post_status use."""

    def __init__(self, root):
        self.root = root
        self.toolbar = MagicMock()

    def run_on_ui_thread(self, fn) -> None:
        VoiceForgeApp.run_on_ui_thread(self, fn)

    def post_status(self, message: str) -> None:
        # Reuse the real implementation so _UIStatusHandler tests exercise it too.
        VoiceForgeApp.post_status(self, message)


def test_run_on_ui_thread_schedules_via_root_after():
    fake = _FakeApp(_FakeRoot())
    called = []
    VoiceForgeApp.run_on_ui_thread(fake, lambda: called.append("ran"))

    assert len(fake.root.scheduled) == 1
    fake.root.scheduled[0]()  # simulate the Tk main loop running it
    assert called == ["ran"]


def test_run_on_ui_thread_swallows_runtime_error_when_window_gone():
    fake = _FakeApp(_FakeRoot(raise_on_after=RuntimeError("main thread is not in main loop")))
    # Must not raise — the worker thread has no one to propagate this to.
    VoiceForgeApp.run_on_ui_thread(fake, lambda: None)


def test_run_on_ui_thread_swallows_tcl_error_when_window_destroyed():
    fake = _FakeApp(_FakeRoot(raise_on_after=TclError("bad window path name")))
    VoiceForgeApp.run_on_ui_thread(fake, lambda: None)


def test_post_status_calls_toolbar_show_message_via_root_after():
    fake = _FakeApp(_FakeRoot())
    VoiceForgeApp.post_status(fake, "Playing")

    assert len(fake.root.scheduled) == 1
    fake.root.scheduled[0]()
    fake.toolbar.show_message.assert_called_once_with("Playing")


def test_ui_status_handler_forwards_tagged_records_only():
    fake = _FakeApp(_FakeRoot())
    handler = _UIStatusHandler(fake)
    log = logging.getLogger("test_ui_status_handler")
    log.addHandler(handler)
    log.setLevel(logging.WARNING)
    try:
        log.warning("plain message, no ui_status")
        log.warning("tagged message", extra={"ui_status": "Something happened"})
    finally:
        log.removeHandler(handler)

    assert len(fake.root.scheduled) == 1
    fake.root.scheduled[0]()
    fake.toolbar.show_message.assert_called_once_with("Something happened")


def test_ui_status_handler_shows_each_distinct_message_only_once():
    """Regression test: a condition logged on every preview/export call (e.g.
    a missing optional dependency) must not spam the status bar forever."""
    fake = _FakeApp(_FakeRoot())
    handler = _UIStatusHandler(fake)
    log = logging.getLogger("test_ui_status_handler_once")
    log.addHandler(handler)
    log.setLevel(logging.WARNING)
    try:
        for _ in range(5):
            log.warning("repeated", extra={"ui_status": "Formant shift unavailable"})
    finally:
        log.removeHandler(handler)

    assert len(fake.root.scheduled) == 1


def test_on_close_removes_status_handler_from_root_logger(monkeypatch, tmp_path):
    """Regression test: _status_handler was added to the root logger in
    __init__ with nothing removing it on close — closing the window used to
    leave a dead handler (holding a reference to the destroyed root/toolbar)
    on the root logger for the rest of the process's life."""
    monkeypatch.setattr(app_module, "SESSION_FILE", str(tmp_path / "session.json"))

    fake = _FakeApp(_FakeRoot())
    fake.params = MagicMock(to_dict=lambda: {})
    fake._status_handler = _UIStatusHandler(fake)
    root_logger = logging.getLogger()
    root_logger.addHandler(fake._status_handler)
    try:
        assert fake._status_handler in root_logger.handlers
        VoiceForgeApp._on_close(fake)
        assert fake._status_handler not in root_logger.handlers
        fake.root.destroy.assert_called_once()
    finally:
        root_logger.removeHandler(fake._status_handler)  # no-op if already removed
