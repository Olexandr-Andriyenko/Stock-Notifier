# src/app/state.py
import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger("stock-alerts")

def load_state(path: Path) -> Dict[str, str]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            logger.debug("State geladen: %s", data)
            return data
        except Exception as e:
            logger.warning("Konnte State nicht laden (%s). Starte mit leerem Dict.", e)
            return {}
    return {}

def save_state(path: Path, state: Dict[str, str]) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.debug("State gespeichert: %s", state)
