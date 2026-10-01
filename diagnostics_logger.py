import logging
import os
import sys
import tempfile
import threading
import traceback
from pathlib import Path


def log_file_path(app_name: str = "VoiceForge") -> Path:
    """Where this app's log file lives.

    Windows: %LOCALAPPDATA%\\<app_name>\\logs\\app.log
    Other platforms, or if LOCALAPPDATA isn't set: ~/.local/state/<app_name>/logs/app.log

    Previously this wrote to ~/.claude/session-data/<date>/exe_<app_name>.log, which is a
    personal AI-dev-tooling path that has no meaning for someone who just downloaded the
    release exe. This matches the convention used by VideoTranscriber's setup_logging().
    """
    local_appdata = os.environ.get("LOCALAPPDATA")
    if sys.platform == "win32" and local_appdata:
        base = Path(local_appdata) / app_name
    else:
        base = Path.home() / ".local" / "state" / app_name
    return base / "logs" / "app.log"


def bootstrap(app_name: str = "VoiceForge") -> None:
    log_path = log_file_path(app_name)
    handlers: list[logging.Handler] = []
    log_dir_error: OSError | None = None
    resolved_path = log_path
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    except OSError as exc:
        log_dir_error = exc
        # Primary log dir is unusable (locked, read-only, OneDrive sync lock,
        # permissions, ...). In a frozen/windowed build sys.stdout is also
        # None, so without a fallback handler here logging.basicConfig would
        # install zero handlers — meaning this warning, and every crash
        # report from the excepthooks below, would vanish completely instead
        # of just losing one convenience. Fall back to the OS temp dir, which
        # is writable in effectively every real scenario.
        try:
            resolved_path = Path(tempfile.gettempdir()) / app_name / "logs" / "app.log"
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(resolved_path, encoding="utf-8"))
        except OSError as fallback_exc:
            log_dir_error = fallback_exc
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )

    if log_dir_error is not None:
        logging.warning(f"Could not open primary log file {log_path}: {log_dir_error}")
    if resolved_path != log_path:
        logging.warning(f"Logging to fallback path instead: {resolved_path}")

    frozen = getattr(sys, "frozen", False)
    logging.info(
        f"STARTUP {app_name} python={sys.version.split()[0]} frozen={frozen} argv={sys.argv}"
    )

    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.critical(
            f"CRASH {app_name} argv={sys.argv} frozen={frozen}\n"
            + "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        )

    sys.excepthook = handle_exception

    def handle_thread_exception(args: threading.ExceptHookArgs) -> None:
        # threading.excepthook's default behavior already prints to stderr, which
        # a windowed exe has none of — without this, a crash in a background
        # thread (e.g. the preview-processing worker in app.py) would vanish
        # completely instead of reaching the log.
        if issubclass(args.exc_type, SystemExit):
            return
        thread_name = args.thread.name if args.thread is not None else "?"
        logging.critical(
            f"CRASH {app_name} thread={thread_name} argv={sys.argv} frozen={frozen}\n"
            + "".join(
                traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
            )
        )

    threading.excepthook = handle_thread_exception
