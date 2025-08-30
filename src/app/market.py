# src/app/market.py
import time
import yfinance as yf
import logging
from typing import Tuple

logger = logging.getLogger("stock-alerts")


def get_open_and_last(ticker: str) -> Tuple[float, float]:
    """
    Retrieve today's opening price and the latest available price for a ticker.

    Strategy:
      1. Try intraday data with finer intervals ("1m", "5m", "15m").
         - Use the very first "Open" of the day.
         - Use the most recent "Close" (last candle).
         - Retry once per interval in case Yahoo delivers empty DataFrames.
      2. If no intraday data is available (e.g., market closed),
         fall back to daily interval ("1d").

    Args:
        ticker (str): Stock symbol, e.g. "AAPL", "SAP.DE", "QQQ", "^GDAXI".

    Returns:
        Tuple[float, float]: (open_today, last_price)

    Raises:
        RuntimeError: If no data is available at all for the ticker.

    Notes:
        - auto_adjust=False → we want raw OHLC values (not split/dividend adjusted).
        - A small sleep (0.4s) between retries reduces API stress
          and avoids "empty DataFrame" glitches from yfinance.
    """
    # --- Try intraday data first ---
    for interval in ("1m", "5m", "15m"):
        for attempt in range(2):  # up to 2 attempts per interval
            df = yf.Ticker(ticker).history(
                period="1d", interval=interval, auto_adjust=False
            )
            if not df.empty:
                open_today = float(df.iloc[0]["Open"])
                last_price = float(df.iloc[-1]["Close"])
                logger.debug(
                    "Intraday %s: interval=%s open=%.4f last=%.4f",
                    ticker, interval, open_today, last_price,
                )
                return open_today, last_price
            logger.debug(
                "Empty intraday data (%s, %s), retry %d",
                ticker, interval, attempt + 1,
            )
            time.sleep(0.4)  # wait before retrying

    # --- Fallback: daily data ---
    df = yf.Ticker(ticker).history(period="1d", interval="1d", auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"No data available for {ticker}")

    row = df.iloc[-1]
    open_today, last_price = float(row["Open"]), float(row["Close"])
    logger.debug(
        "Fallback daily data %s: open=%.4f last=%.4f",
        ticker, open_today, last_price,
    )
    return open_today, last_price
