import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import LOG_DIR, LOG_LEVEL


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging():
    logger = logging.getLogger("nfe_scanner")
    if logger.handlers:
        return logger

    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        Path(LOG_DIR) / "nfe_scanner.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def mask_access_key(value: str | None) -> str:
    if not value:
        return "ausente"
    value = str(value)
    if len(value) <= 12:
        return "***"
    return f"{value[:6]}...{value[-6:]}"
