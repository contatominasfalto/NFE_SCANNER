import logging

from .config import LOG_LEVEL


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
    return logger


def mask_access_key(value: str | None) -> str:
    if not value:
        return "ausente"
    value = str(value)
    if len(value) <= 12:
        return "***"
    return f"{value[:6]}...{value[-6:]}"
