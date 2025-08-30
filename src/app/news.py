from __future__ import annotations
import datetime as dt
from typing import List, Dict, Iterable
from urllib.parse import quote_plus
import feedparser


def build_query(name: str, ticker: str) -> str:
    """
    Build a Google News search query for a company.

    Strategy:
      - Search for either the company name OR the ticker.
      - Add finance-related context keywords (stock, aktie, börse)
        to filter out irrelevant results.

    Example:
        build_query("Apple", "AAPL")
        -> ("Apple" OR AAPL) (stock OR aktie OR börse)

    Args:
        name (str): Clean company name (e.g. "Apple").
        ticker (str): Stock ticker (e.g. "AAPL").

    Returns:
        str: Search query string for Google News.
    """
    return f'("{name}" OR {ticker}) (stock OR aktie OR börse)'


def filter_titles(items: List[Dict[str, str]], required_keywords: Iterable[str] = ()) -> List[Dict[str, str]]:
    """
    Filter news items so that only those containing required keywords
    in their title are kept.

    Args:
        items (List[Dict]): List of news dicts (must contain "title").
        required_keywords (Iterable[str]): Keywords that must appear
            in the title (case-insensitive).

    Returns:
        List[Dict]: Filtered list of items that match at least one keyword.
    """
    if not required_keywords:
        return items

    out = []
    req = [k.lower() for k in required_keywords if k]
    for it in items:
        title = (it.get("title") or "").lower()
        if any(k in title for k in req):
            out.append(it)
    return out


def _google_news_rss_url(query: str, lang: str = "de", country: str = "DE") -> str:
    """
    Build a Google News RSS URL for a given query.

    Args:
        query (str): Search query.
        lang (str): Language code, e.g. "de" (German), "en" (English).
        country (str): Country code, e.g. "DE", "US".

    Returns:
        str: Full Google News RSS feed URL.
    """
    # "when:12h" restricts to articles published in the last 12 hours
    q = quote_plus(f"{query} when:12h")
    return f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={country}&ceid={country}:{lang}"


def fetch_headlines(
    query: str,
    limit: int = 2,
    lookback_hours: int = 12,
    lang: str = "de",
    country: str = "DE",
) -> List[Dict[str, str]]:
    """
    Fetch latest headlines from Google News RSS for a given query.

    Args:
        query (str): Search query (usually built with `build_query`).
        limit (int): Maximum number of news items to return.
        lookback_hours (int): Only include news not older than this.
        lang (str): Language code (e.g. "de", "en").
        country (str): Country code (e.g. "DE", "US").

    Returns:
        List[Dict[str, str]]: News items in the format:
            {
              "title": "Some headline",
              "source": "Publisher",
              "link": "https://original-article.com",
              "published": "2025-08-30T10:45:00+00:00"
            }

    Notes:
        - Uses `feedparser` to parse Google News RSS feeds.
        - Adds some buffer (fetch up to 3x requested items)
          before filtering out old articles.
        - Published time is ISO-8601 with UTC timezone if available.
    """
    url = _google_news_rss_url(query, lang=lang, country=country)
    feed = feedparser.parse(url)

    out: List[Dict[str, str]] = []
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=lookback_hours)

    for e in feed.entries[: max(10, limit * 3)]:  # buffer, then filter
        title = getattr(e, "title", "").strip()
        link = getattr(e, "link", "").strip()

        # Extract publisher/source if available
        source = ""
        if hasattr(e, "source") and getattr(e.source, "title", ""):
            source = e.source.title
        elif hasattr(e, "tags") and e.tags:
            source = e.tags[0].term

        # Filter by publication date (if present)
        published = ""
        if hasattr(e, "published_parsed") and e.published_parsed:
            pub_dt = dt.datetime(*e.published_parsed[:6], tzinfo=dt.timezone.utc)
            if pub_dt < cutoff:
                continue  # too old
            published = pub_dt.isoformat()

        if title and link:
            out.append(
                {
                    "title": title,
                    "source": source,
                    "link": link,
                    "published": published,
                }
            )
        if len(out) >= limit:
            break

    return out
