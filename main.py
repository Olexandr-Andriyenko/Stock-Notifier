from pathlib import Path
from src.app.config import load_config
from src.app.logging_setup import setup_logging
from src.app.core import run_once
from src.app.utils import mask_secret


def main():
    """
    Entry point of the Stock Notifier application.

    - Loads configuration from `config.json`.
    - Sets up logging (console/file depending on config).
    - Runs one monitoring cycle (`run_once`), which:
        * Checks if the market is open (with test bypass if enabled).
        * Fetches stock/ETF prices using yfinance.
        * Compares current price to opening price.
        * Sends push notifications via ntfy if thresholds are exceeded.
        * Optionally fetches related news headlines.
    """
    # Load configuration (tickers, thresholds, logging settings, etc.)
    cfg = load_config("config.json")

    # Initialize logging system (console/file based on config.json)
    logger = setup_logging(cfg["log"])

    # Log current configuration (with secrets masked)
    logger.info(
        "Configuration loaded: ntfy.server=%s | ntfy.topic(masked)=%s | log.level=%s",
        cfg["ntfy"]["server"],
        mask_secret(cfg["ntfy"]["topic"]),
        cfg["log"]["level"]
    )

    # Run one monitoring cycle:
    # - Price check
    # - Threshold detection
    # - Notification (ntfy + news)
    run_once(
        tickers=cfg["tickers"],
        threshold_pct=float(cfg["threshold_pct"]),
        ntfy_server=cfg["ntfy"]["server"],
        ntfy_topic=cfg["ntfy"]["topic"],
        state_file=Path(cfg["state_file"]),
        market_hours_cfg=cfg["market_hours"],
        test_cfg=cfg["test"],
        news_cfg=cfg["news"]
    )


if __name__ == "__main__":
    main()
