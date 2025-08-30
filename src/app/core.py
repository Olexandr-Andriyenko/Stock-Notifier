# src/app/core.py
import datetime as dt
from zoneinfo import ZoneInfo
import logging
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urlparse, parse_qs
import requests

from .market import get_open_and_last
from .ntfy import notify_ntfy
from .state import load_state, save_state
from .company import auto_keywords
from .news import fetch_headlines, build_query, filter_titles

logger = logging.getLogger("stock-alerts")


def _ticker_to_query(ticker: str, override_name: str | None = None) -> str:
    """
    Return a human-friendly query term for a ticker.

    Args:
        ticker: Raw ticker symbol (e.g., "AAPL").
        override_name: Optional override (e.g., "Apple").

    Returns:
        A display/query string; override_name if provided, else the ticker.
    """
    return override_name or ticker


def _ensure_https(u: str) -> str:
    """
    Ensure the given URL has a scheme. If missing, prefix with https://

    This helps when feeds provide bare domains or schemeless URLs.
    """
    if not u:
        return u
    if u.startswith(("http://", "https://")):
        return u
    return "https://" + u


def _extract_original_url(link: str, *, resolve_redirects: bool = True, timeout: float = 3.0) -> str:
    """
    Try to extract the original article URL from Google News redirect links.

    Strategy:
        1) If it's a news.google.com link and contains ?url=..., use that.
        2) Optionally resolve redirects via HEAD (fallback GET) to obtain the final URL.
        3) If all fails, return the input link.

    Args:
        link: Possibly a Google News RSS link.
        resolve_redirects: Whether to follow redirects to the final URL.
        timeout: Per-request timeout in seconds.

    Returns:
        A best-effort "clean" URL pointing to the original source.
    """
    try:
        link = _ensure_https(link)
        p = urlparse(link)
        if "news.google.com" in p.netloc:
            qs = parse_qs(p.query)
            if "url" in qs and qs["url"]:
                return _ensure_https(qs["url"][0])

            if resolve_redirects:
                try:
                    # HEAD first (cheap), some hosts require GET
                    r = requests.head(link, allow_redirects=True, timeout=timeout)
                    if r.url and r.url != link:
                        return _ensure_https(r.url)
                    if r.status_code in (403, 405):
                        g = requests.get(link, allow_redirects=True, timeout=timeout, stream=True)
                        if g.url and g.url != link:
                            return _ensure_https(g.url)
                except requests.RequestException:
                    pass
        return link
    except Exception:
        return link


def _domain(url: str) -> str:
    """
    Extract a pretty domain (strip leading 'www.') from a URL for compact display.
    """
    try:
        d = urlparse(url).netloc
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return url


def _format_headlines(items: List[Dict[str, Any]]) -> str:
    """
    Build a compact Markdown block for headlines.

    - Web (ntfy web app): Markdown will be rendered (nice links)
    - Mobile (ntfy apps): Markdown shows as plain text, so we also include
      a short, real URL line that remains clickable on phones.

    Returns:
        A multi-line string ready to embed into the notification body.
    """
    if not items:
        return ""
    lines: List[str] = []
    for it in items:
        title = (it.get("title") or "").strip()
        src   = f" — {it['source']}" if it.get("source") else ""
        link  = _ensure_https((it.get("link") or "").strip())
        if link:
            orig = _extract_original_url(link)
            dom  = _domain(orig)
            # Markdown title link for web, plus a short real URL for mobile
            lines.append(f"• [{title}]({orig}){src}\n   🔗 {orig if len(orig) <= 60 else 'https://' + dom}")
        else:
            lines.append(f"• {title}{src}")
    return "\n".join(lines)


def now_tz(tz: str) -> dt.datetime:
    """
    Get current date/time in a specific timezone (e.g., 'Europe/Berlin').

    Using timezone-aware datetimes avoids DST pitfalls and makes logging consistent.
    """
    return dt.datetime.now(ZoneInfo(tz))


def is_market_hours(cfg_mh: dict) -> bool:
    """
    Heuristic market-hours check (simple window, no holidays).

    Args:
        cfg_mh: Market hours config with keys:
            - enabled (bool)
            - tz (str)
            - start_hour (int)
            - end_hour (int)
            - days_mon_to_fri_only (bool)

    Returns:
        True if within the configured hours, else False.
    """
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
    """
    Execute one monitoring cycle:
      - Check market hours (with optional test bypass)
      - For each ticker:
          * Fetch open & last price (intraday preferred)
          * Compute Δ% vs. open
          * Trigger ntfy push if |Δ%| ≥ threshold (with de-bounce via state file)
          * Optionally attach compact news headlines (with cleaned source URLs)

    Side effects:
      - Sends an HTTP POST to ntfy (unless dry_run)
      - Reads/writes the alert state JSON (anti-spam)
      - Writes logs according to logging setup
    """
    start_ts = now_tz(market_hours_cfg["tz"]).strftime("%Y-%m-%d %H:%M:%S")
    logger.info("Job start (%s), Ticker=%s, Schwelle=±%.1f%%", start_ts, ",".join(tickers), threshold_pct)

    within = is_market_hours(market_hours_cfg)
    if test_cfg.get("enabled") and test_cfg.get("bypass_market_hours"):
        logger.info("Test mode enabled: bypassing market-hours window.")
        within = True
    logger.info("Market hours? %s (effective=%s)", is_market_hours(market_hours_cfg), within)
    if not within:
        logger.info("Outside market hours — no push sent.")
        return

    state: Dict[str, str] = load_state(state_file)

    for tk in tickers:
        try:
            open_px, last_px = get_open_and_last(tk)
            if open_px == 0:
                raise RuntimeError(f"Open is 0 for {tk}; cannot compute Δ%.")

            pct = (last_px - open_px) / open_px * 100.0

            # Test override: force a specific delta to simulate alerts
            if test_cfg.get("enabled") and test_cfg.get("force_delta_pct") is not None:
                forced = float(test_cfg["force_delta_pct"])
                logger.info("Test mode: forcing Δ%% (%.2f%%) for %s (was %.2f%%).", forced, tk, pct)
                pct = forced
                last_px = open_px * (1.0 + pct / 100.0)

            logger.info("%s | Last=%.4f Open=%.4f Δ=%+.2f%%", tk, last_px, open_px, pct)

            prev = state.get(tk, "none")
            direction = "up" if pct >= threshold_pct else "down" if pct <= -threshold_pct else "none"

            if direction != "none" and direction != prev:
                # Crossing the threshold for the first time (since last reset) → send alert
                arrow = "📈" if direction == "up" else "📉"
                title = f"Stock Alert: {tk}"
                body  = f"{arrow} {tk}: {pct:+.2f}% vs. Open\nAktuell: {last_px:.2f} | Open: {open_px:.2f}"

                headlines_block = ""
                first_url_for_click = None

                if news_cfg.get("enabled", False):
                    # Build a smarter query from company metadata and filter out false positives
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

                    # Prepare a click target (open first article when tapping the notification)
                    if items:
                        cand = _ensure_https(items[0].get("link", ""))
                        first_url_for_click = _extract_original_url(cand)

                    news_text = _format_headlines(items)
                    if not news_text:
                        # Fallback: try en/US if DE results are weak or empty
                        items = fetch_headlines(
                            query=q,
                            limit=int(news_cfg.get("limit", 2)),
                            lookback_hours=max(12, int(news_cfg.get("lookback_hours", 12))),
                            lang=news_cfg.get("fallback_lang", "en"),
                            country=news_cfg.get("fallback_country", "US"),
                        )
                        items = filter_titles(items, required_keywords=req_kw)

                        if items and not first_url_for_click:
                            cand = _ensure_https(items[0].get("link", ""))
                            first_url_for_click = _extract_original_url(cand)

                        news_text = _format_headlines(items)

                    if news_text:
                        headlines_block = "\n\n📰 News:\n" + news_text

                msg = body + headlines_block

                # Send notification (Markdown on web; mobile gets real URLs + Click target)
                notify_ntfy(
                    ntfy_server,
                    ntfy_topic,
                    title,
                    msg,
                    dry_run=test_cfg.get("dry_run", False),
                    markdown=True,
                    click_url=first_url_for_click,
                )

                # Persist state so we don't spam until price returns to corridor
                state[tk] = direction
                save_state(state_file, state)

            elif direction == "none":
                # Back in corridor: reset state so we can alert again on next breakout
                if prev != "none":
                    logger.info("Back in corridor (%s): reset state %s → none", tk, prev)
                    state[tk] = "none"
                    save_state(state_file, state)
                else:
                    logger.info("%s | No alert (< ±%.1f%%).", tk, threshold_pct)

            else:
                logger.info("%s | Already alerted (%s). Waiting to re-enter corridor.", tk, prev)

        except Exception as e:
            # Catch-all to ensure a single bad ticker doesn't break the entire run
            logger.error("Error while processing %s: %s", tk, e)
