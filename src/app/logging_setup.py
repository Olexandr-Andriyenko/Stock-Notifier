# src/app/logging_setup.py
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any

def setup_logging(cfg_log: Dict[str, Any]) -> logging.Logger:
    level_name = str(cfg_log.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logger = logging.getLogger("stock-alerts")
    logger.setLevel(level)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

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

    logger.debug("Logging initialisiert: level=%s, to_file=%s", level_name, cfg_log.get("to_file", False))
    return logger
