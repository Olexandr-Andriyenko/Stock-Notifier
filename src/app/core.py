# src/app/core.py
import datetime as dt
from zoneinfo import ZoneInfo
import logging
from pathlib import Path
from typing import Dict, List
from .news import fetch_headlines

from .market import get_open_and_last
from .ntfy import notify_ntfy
from .state import load_state, save_state
from .company import auto_keywords
from .news import fetch_headlines, build_query, filter_titles

logger = logging.getLogger("stock-alerts")

def _ticker_to_query(ticker: str, override_name: str | None = None) -> str:
    # ganz simpel: nutze override_name oder Fallback = Ticker
    return override_name or ticker

def _format_headlines(items) -> str:
    # einzeilig, kurz; ntfy-Nachrichten sollen kompakt bleiben
    if not items: 
        return ""
    lines = []
    for it in items:
        src = f" — {it['source']}" if it.get("source") else ""
        lines.append(f"• {it['title']}{src}")
    return "\n".join(lines)

def now_tz(tz: str) -> dt.datetime:
    return dt.datetime.now(ZoneInfo(tz))

def is_market_hours(cfg_mh: dict) -> bool:
    if not cfg_mh.get("enabled", True):
        return True
    n = now_tz(cfg_mh["tz"])
    if cfg_mh.get("days_mon_to_fri_only", True) and n.weekday() >= 5:
        return False
    return int(cfg_mh["start_hour"]) <= n.hour < int(cfg_mh["end_hour"])

def run_once(
    tickers: List[str],
    threshold_pct: float,
    ntfy_server: str,
    ntfy_topic: str,
    state_file: Path,
    market_hours_cfg: dict,
    test_cfg: dict,
    news_cfg: dict,
) -> None:
    """Ein Lauf: prüft alle Ticker, sendet ggf. ntfy, pflegt State."""
    start_ts = now_tz(market_hours_cfg["tz"]).strftime("%Y-%m-%d %H:%M:%S")
    logger.info("Job start (%s), Ticker=%s, Schwelle=±%.1f%%", start_ts, ",".join(tickers), threshold_pct)

    within = is_market_hours(market_hours_cfg)
    if test_cfg.get("enabled") and test_cfg.get("bypass_market_hours"):
        logger.info("Testmodus aktiv: Handelszeiten-Bypass eingeschaltet.")
        within = True
    logger.info("Handelszeit? %s (effective=%s)", is_market_hours(market_hours_cfg), within)
    if not within:
        logger.info("Außerhalb der Handelszeiten – kein Push gesendet.")
        return

    state: Dict[str, str] = load_state(state_file)
    for tk in tickers:
        try:
            open_px, last_px = get_open_and_last(tk)
            if open_px == 0:
                raise RuntimeError(f"Open ist 0 für {tk}; kann Δ% nicht berechnen.")
            pct = (last_px - open_px) / open_px * 100.0

            if test_cfg.get("enabled") and test_cfg.get("force_delta_pct") is not None:
                forced = float(test_cfg["force_delta_pct"])
                logger.info("Testmodus: erzwungene Δ%% (%.2f%%) für %s (statt %.2f%%).", forced, tk, pct)
                pct = forced
                last_px = open_px * (1.0 + pct / 100.0)

            logger.info("%s | Last=%.4f Open=%.4f Δ=%+.2f%%", tk, last_px, open_px, pct)

            prev = state.get(tk, "none")
            direction = "up" if pct >= threshold_pct else "down" if pct <= -threshold_pct else "none"

            if direction != "none" and direction != prev:
                arrow = "📈" if direction == "up" else "📉"
                title = f"Stock Alert: {tk}"
                body = f"{arrow} {tk}: {pct:+.2f}% vs. Open\nAktuell: {last_px:.2f} | Open: {open_px:.2f}"

                headlines_block = ""
                if news_cfg.get("enabled", False):
                    company_name, req_kw = auto_keywords(tk)
                    q = build_query(company_name, tk)
                    items = fetch_headlines(
                        query=q,
                        limit=int(news_cfg.get("limit", 2)),
                        lookback_hours=int(news_cfg.get("lookback_hours", 12)),
                        lang=news_cfg.get("lang", "de"),
                        country=news_cfg.get("country", "DE"),
                    )
                    items = filter_titles(items, required_keywords=req_kw)
                    news_text = _format_headlines(items)
                    if not news_text:
                        # Fallback: eng/US nochmal probieren
                        items = fetch_headlines(
                            query=q,
                            limit=int(news_cfg.get("limit", 2)),
                            lookback_hours=max(12, int(news_cfg.get("lookback_hours", 12))),
                            lang=news_cfg.get("fallback_lang", "en"),
                            country=news_cfg.get("fallback_country", "US"),
                        )
                        items = filter_titles(items, required_keywords=req_kw)
                        news_text = _format_headlines(items)

                    if news_text:
                        headlines_block = "\n\n📰 News:\n" + news_text

                msg = body + headlines_block
                notify_ntfy(ntfy_server, ntfy_topic, title, msg, dry_run=test_cfg.get("dry_run", False))
                state[tk] = direction
                save_state(state_file, state)

            elif direction == "none":
                if prev != "none":
                    logger.info("Zurück im Korridor (%s): Reset State %s → none", tk, prev)
                    state[tk] = "none"
                    save_state(state_file, state)
                else:
                    logger.info("%s | Keine Benachrichtigung (< ±%.1f%%).", tk, threshold_pct)

            else:
                logger.info("%s | Bereits gemeldet (%s). Warte auf Rückkehr in den Korridor.", tk, prev)

        except Exception as e:
            logger.error("Fehler bei Verarbeitung von %s: %s", tk, e)

