import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any


def setup_logging(cfg_log: Dict[str, Any]) -> logging.Logger:
    """
    Configure and return the central logger for the app.

    Features:
      - Log level configurable via config (DEBUG, INFO, WARNING, ...)
      - Always logs to console (stdout)
      - Optional rotating file handler:
          * File size limit (maxBytes)
          * Number of backups (backupCount)
          * UTF-8 encoding for international characters

    Args:
        cfg_log: Logging configuration dictionary, expected keys:
            - "level": str, log level (e.g. "INFO", "DEBUG")
            - "to_file": bool, whether to log to a file
            - "file_path": str, log filename (default "alerts.log")
            - "file_max_bytes": int, max file size before rotation
            - "file_backup_count": int, number of rotated backups to keep

    Returns:
        logging.Logger: Configured logger instance ("stock-alerts").
    """
    # Resolve log level from config (fallback to INFO)
    level_name = str(cfg_log.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    # Always use the same logger name throughout the app
    logger = logging.getLogger("stock-alerts")
    logger.setLevel(level)

    # Remove any previously attached handlers (avoid duplicates when re-importing)
    logger.handlers.clear()

    # Define simple log format: timestamp, level, message
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    # --- Console handler (stdout) ---
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # --- Optional rotating file handler ---
    if cfg_log.get("to_file", False):
        fh = RotatingFileHandler(
            cfg_log.get("file_path", "alerts.log"),
            maxBytes=int(cfg_log.get("file_max_bytes", 1_000_000)),
            backupCount=int(cfg_log.get("file_backup_count", 3)),
            encoding="utf-8",
        )
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    logger.debug(
        "Logging initialized: level=%s, to_file=%s",
        level_name,
        cfg_log.get("to_file", False),
    )
    return logger
