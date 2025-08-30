# src/app/config.py
from __future__ import annotations
import os, json
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

DEFAULTS: Dict[str, Any] = {
    "log": {"level": "INFO", "to_file": False, "file_path": "alerts.log", "file_max_bytes": 1_000_000, "file_backup_count": 3},
    "ntfy": {"server": "https://ntfy.sh", "topic": "CHANGE-ME"},
    "tickers": ["AAPL"],
    "threshold_pct": 3.0,
    "state_file": "alert_state.json",
    "market_hours": {"enabled": True, "tz": "Europe/Berlin", "start_hour": 8, "end_hour": 22, "days_mon_to_fri_only": True},
    "test": {"enabled": False, "bypass_market_hours": True, "force_delta_pct": None, "dry_run": False},
}

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def load_config(path: str = "config.json") -> Dict[str, Any]:
    """Lädt .env, dann config.json, mergen mit Defaults, minimale Validierung."""
    load_dotenv()  # lädt .env im Projekt-Root
    user = {}
    p = Path(path)
    if p.exists():
        try:
            user = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise RuntimeError(f"config.json konnte nicht gelesen werden: {e}")

    cfg = deep_merge(DEFAULTS, user)

    # ENV-Overrides (praktisch beim Debuggen / Secrets)
    if os.getenv("LOG_LEVEL"):
        cfg["log"]["level"] = os.getenv("LOG_LEVEL")
    if os.getenv("NTFY_SERVER"):
        cfg["ntfy"]["server"] = os.getenv("NTFY_SERVER")
    if os.getenv("NTFY_TOPIC"):
        cfg["ntfy"]["topic"]  = os.getenv("NTFY_TOPIC")

    # minimale Validation
    if not cfg["ntfy"]["topic"] or cfg["ntfy"]["topic"] == "CHANGE-ME":
        raise RuntimeError("Bitte ein geheimes ntfy Topic setzen (ntfy.topic oder .env NTFY_TOPIC).")
    if not cfg["tickers"]:
        raise RuntimeError("config.tickers darf nicht leer sein.")
    return cfg
