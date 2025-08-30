from pathlib import Path
from src.app.config import load_config
from src.app.logging_setup import setup_logging
from src.app.core import run_once

def main():
    cfg = load_config("config.json")
    logger = setup_logging(cfg["log"])

    def mask_secret(s: str, keep: int = 4) -> str:
        if not s: return "(unset)"
        return "..."

    logger.info(
        "Konfiguration: ntfy.server=%s | ntfy.topic(masked)=%s | log.level=%s",
        cfg["ntfy"]["server"], mask_secret(cfg["ntfy"]["topic"]), cfg["log"]["level"]
    )

    run_once(
        tickers=cfg["tickers"],
        threshold_pct=float(cfg["threshold_pct"]),
        ntfy_server=cfg["ntfy"]["server"],
        ntfy_topic=cfg["ntfy"]["topic"],
        state_file=Path(cfg["state_file"]),
        market_hours_cfg=cfg["market_hours"],
        test_cfg=cfg["test"],
    )

if __name__ == "__main__":
    main()
