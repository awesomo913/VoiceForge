import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path


def bootstrap(app_name: str = "VoiceForge") -> None:
    log_dir = Path.home() / ".claude" / "session-data" / datetime.now().strftime("%Y-%m-%d")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"exe_{app_name}.log"

    handlers = [logging.FileHandler(log_file, encoding="utf-8")]
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )

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
