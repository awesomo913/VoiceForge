import logging
import os
import sys
import threading

import pytest

import diagnostics_logger as dl


@pytest.fixture(autouse=True)
def _restore_logging_state():
    """bootstrap() mutates global state (root logger handlers, sys.excepthook,
    threading.excepthook) — snapshot and restore it so these tests don't leak
    into other tests or into the real app if run interleaved."""
    root = logging.getLogger()
    prev_handlers = list(root.handlers)
    prev_level = root.level
    prev_excepthook = sys.excepthook
    prev_thread_excepthook = threading.excepthook
    yield
    root.handlers = prev_handlers
    root.setLevel(prev_level)
    sys.excepthook = prev_excepthook
    threading.excepthook = prev_thread_excepthook


def test_log_file_path_uses_localappdata_on_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(dl.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = dl.log_file_path("VoiceForge")
    assert path == tmp_path / "VoiceForge" / "logs" / "app.log"


def test_log_file_path_falls_back_when_localappdata_missing(monkeypatch):
    monkeypatch.setattr(dl.sys, "platform", "win32")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    path = dl.log_file_path("VoiceForge")
    expected_suffix = os.sep.join([".local", "state", "VoiceForge", "logs", "app.log"])
    assert str(path).endswith(expected_suffix)


def test_log_file_path_is_not_the_old_claude_dev_path(monkeypatch, tmp_path):
    """Regression test: this used to write under ~/.claude/session-data/<date>/,
    a personal AI-dev-tooling path with no meaning to someone who just
    downloaded the release exe."""
    monkeypatch.setattr(dl.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = dl.log_file_path("VoiceForge")
    assert ".claude" not in str(path)
    assert "session-data" not in str(path)


def test_bootstrap_creates_log_file_and_writes_startup_line(monkeypatch, tmp_path):
    monkeypatch.setattr(dl.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    dl.bootstrap("TestApp")

    log_path = tmp_path / "TestApp" / "logs" / "app.log"
    assert log_path.is_file()
    content = log_path.read_text(encoding="utf-8")
    assert "STARTUP TestApp" in content


def test_bootstrap_installs_thread_excepthook(monkeypatch, tmp_path):
    monkeypatch.setattr(dl.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    dl.bootstrap("TestApp")

    assert threading.excepthook is not threading.__excepthook__
    assert sys.excepthook is not sys.__excepthook__


def test_bootstrap_falls_back_to_temp_dir_when_primary_log_dir_unusable(monkeypatch, tmp_path):
    """Regression test: if the primary log dir can't be created/opened AND
    sys.stdout is None (a frozen windowed exe), bootstrap() used to end up
    with zero logging handlers — logging.basicConfig(handlers=[]) silently
    drops everything, including the very warning about the failure and every
    later crash report. There must always be at least one real handler."""
    # A *file* where LOCALAPPDATA/<app_name> needs to be a directory makes
    # Path.mkdir(parents=True) raise NotADirectoryError (an OSError) reliably
    # cross-platform.
    blocked = tmp_path / "blocked_localappdata"
    blocked.write_text("not a directory")
    monkeypatch.setattr(dl.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(blocked))

    fake_temp_dir = tmp_path / "faketemp"
    fake_temp_dir.mkdir()
    monkeypatch.setattr(dl.tempfile, "gettempdir", lambda: str(fake_temp_dir))
    monkeypatch.setattr(dl.sys, "stdout", None)

    dl.bootstrap("TestApp")

    root = logging.getLogger()
    assert len(root.handlers) >= 1, "bootstrap() must never leave zero log handlers"

    fallback_log = fake_temp_dir / "TestApp" / "logs" / "app.log"
    assert fallback_log.is_file()
    content = fallback_log.read_text(encoding="utf-8")
    assert "STARTUP TestApp" in content
    assert "Could not open primary log file" in content


def test_thread_excepthook_logs_crash_with_thread_name(monkeypatch, tmp_path):
    """Regression test: a worker-thread crash (e.g. app.py's preview-processing
    thread) used to disappear silently — threading.excepthook was never set,
    so a windowed exe (no stderr) had nowhere for it to go."""
    monkeypatch.setattr(dl.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    dl.bootstrap("TestApp")

    t = threading.Thread(target=lambda: None, name="worker-1")
    # Simulate what the threading module does when a thread's target raises,
    # without actually spawning a thread (keeps this test deterministic).
    try:
        raise ValueError("boom from worker thread")
    except ValueError:
        hook_args = threading.ExceptHookArgs((*sys.exc_info(), t))
        threading.excepthook(hook_args)

    log_path = tmp_path / "TestApp" / "logs" / "app.log"
    content = log_path.read_text(encoding="utf-8")
    assert "CRASH TestApp thread=worker-1" in content
    assert "boom from worker thread" in content
