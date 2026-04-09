# Logging helper class, writes to the ./log directory 
# to disable logging (as it gets heavy) use the --no-log flag when 
# training models
from __future__ import annotations

import logging
from pathlib import Path


_LOGGERS: dict[str, logging.Logger] = {}
_LOGGING_ENABLED = True


def set_logging_enabled(enabled: bool) -> None:
    """Enable or disable project logging globally."""
    global _LOGGING_ENABLED
    _LOGGING_ENABLED = enabled

    # Update already-created loggers so the flag takes effect immediately.
    for logger in _LOGGERS.values():
        logger.disabled = not enabled


def get_logger(name: str) -> logging.Logger:
    if name in _LOGGERS:
        _LOGGERS[name].disabled = not _LOGGING_ENABLED
        return _LOGGERS[name]

    project_root = Path(__file__).resolve().parents[1]
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.disabled = not _LOGGING_ENABLED

    if not logger.handlers:
        file_handler = logging.FileHandler(log_dir / "blackjack.log", encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _LOGGERS[name] = logger
    return logger
