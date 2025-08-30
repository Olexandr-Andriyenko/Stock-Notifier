# src/app/news.py
from __future__ import annotations
import datetime as dt
from typing import List, Dict
from urllib.parse import quote_plus
import feedparser
from typing import Iterable

def build_query(name: str, ticker: str) -> str:
    # exakter Name ODER Ticker + Finanzkontext
    # z. B. ("Apple" OR AAPL) (stock OR aktie OR börse)
    return f'("{name}" OR {ticker}) (stock OR aktie OR börse)'

def filter_titles(items, required_keywords: Iterable[str] = ()):
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
    # "when:12h" begrenzt auf letzte 12h; anpassbar im Code
    q = quote_plus(f'{query} when:12h')
    return f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={country}&ceid={country}:{lang}"

def fetch_headlines(query: str, limit: int = 2, lookback_hours: int = 12,
                    lang: str = "de", country: str = "DE") -> List[Dict[str, str]]:
    """
    Liefert bis zu 'limit' News-Items: {title, source, link, published}
    """
    url = _google_news_rss_url(query, lang=lang, country=country)
    feed = feedparser.parse(url)

    out: List[Dict[str, str]] = []
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=lookback_hours)

    for e in feed.entries[: max(10, limit*3)]:  # etwas Puffer, wir filtern gleich
        title = getattr(e, "title", "").strip()
        link  = getattr(e, "link", "").strip()

        # Quelle (Publisher) aus 'source' oder aus 'title_detail' ableiten
        source = ""
        if hasattr(e, "source") and getattr(e.source, "title", ""):
            source = e.source.title
        elif hasattr(e, "tags") and e.tags:
            source = e.tags[0].term

        # Veröffentlichungszeit (falls vorhanden)
        published = ""
        if hasattr(e, "published_parsed") and e.published_parsed:
            pub_dt = dt.datetime(*e.published_parsed[:6], tzinfo=dt.timezone.utc)
            if pub_dt < cutoff:
                continue
            published = pub_dt.isoformat()

        if title and link:
            out.append({"title": title, "source": source, "link": link, "published": published})
        if len(out) >= limit:
            break
    return out
