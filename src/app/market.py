# src/app/market.py
import time
import yfinance as yf
import logging
from typing import Tuple

logger = logging.getLogger("stock-alerts")

def get_open_and_last(ticker: str) -> Tuple[float, float]:
    """Ermittelt Tages-Open und letzten Preis (Intraday bevorzugt, 1 Retry)."""
    for interval in ("1m", "5m", "15m"):
        for attempt in range(2):
            df = yf.Ticker(ticker).history(period="1d", interval=interval, auto_adjust=False)
            if not df.empty:
                open_today = float(df.iloc[0]["Open"])
                last_price = float(df.iloc[-1]["Close"])
                logger.debug("Intraday %s: %s open=%.4f last=%.4f", ticker, interval, open_today, last_price)
                return open_today, last_price
            logger.debug("Leere Intraday-Daten (%s, %s), Retry %d", ticker, interval, attempt + 1)
            time.sleep(0.4)

    df = yf.Ticker(ticker).history(period="1d", interval="1d", auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"Keine Daten für {ticker}")
    row = df.iloc[-1]
    open_today, last_price = float(row["Open"]), float(row["Close"])
    logger.debug("Fallback Tagesdaten %s: open=%.4f last=%.4f", ticker, open_today, last_price)
    return open_today, last_price
