# src/app/company.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import json
import time
import yfinance as yf

CACHE_FILE = Path("company_cache.json")

# Common legal suffixes often found in company names,
# which we remove to get a cleaner keyword (e.g., "Apple Inc." -> "Apple").
LEGAL_SUFFIXES = {
    "inc", "inc.", "corp", "corp.", "co", "co.", "ltd", "ltd.", "plc",
    "ag", "se", "nv", "sa", "oyj", "ab", "spa", "s.p.a.", "pte", "pteltd",
}


@dataclass
class CompanyMeta:
    """
    Represents metadata about a company/ticker.
    
    Attributes:
        ticker (str): The full ticker symbol, e.g., "SAP.DE".
        name (Optional[str]): Cleaned company name without legal suffixes, e.g., "Apple".
        raw_name (Optional[str]): Original company name as returned by Yahoo Finance, e.g., "Apple Inc.".
        source (str): Source of the name (e.g., "info.longName", "info.shortName", "fallback").
        base_ticker (str): Simplified ticker without suffixes, e.g., "SAP" for "SAP.DE".
    """
    ticker: str
    name: Optional[str]
    raw_name: Optional[str]
    source: str
    base_ticker: str


def _load_cache() -> Dict[str, Any]:
    """Load cached company metadata from JSON file."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    """Save company metadata to local cache file."""
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _strip_legal_suffixes(name: str) -> str:
    """
    Remove common legal suffixes from a company name.

    Example:
        "Apple Inc." -> "Apple"
        "SAP SE" -> "SAP"
    """
    parts = [p.strip(",. ") for p in name.split()]
    while parts and parts[-1].lower() in LEGAL_SUFFIXES:
        parts.pop()
    return " ".join(parts) if parts else name.strip()


def _base_ticker(symbol: str) -> str:
    """
    Extract the base ticker symbol.

    Examples:
        "SAP.DE" -> "SAP"
        "BRK.B"  -> "BRK"
        "^GDAXI" -> "^GDAXI" (indices remain unchanged)
    """
    if symbol.startswith("^"):  # Index tickers like ^GDAXI
        return symbol
    if "." in symbol:
        return symbol.split(".", 1)[0]
    return symbol


def _fetch_yf_info(symbol: str, retries: int = 2, delay: float = 0.4) -> Dict[str, Any]:
    """
    Fetch company information from Yahoo Finance.

    Args:
        symbol (str): Ticker symbol.
        retries (int): Number of retries if request fails.
        delay (float): Delay between retries in seconds.

    Returns:
        dict: Yahoo Finance info dictionary (may be empty if lookup fails).
    """
    last_exc = None
    for _ in range(retries + 1):
        try:
            t = yf.Ticker(symbol)
            # Depending on yfinance version, prefer .get_info() over .info
            info = t.get_info() if hasattr(t, "get_info") else getattr(t, "info", {})
            if info:
                return info
        except Exception as e:
            last_exc = e
            time.sleep(delay)
    return {}


def get_company_meta(symbol: str) -> CompanyMeta:
    """
    Retrieve company metadata (name, base ticker, etc.) with caching and fallbacks.

    Process:
    - Check local cache first (fast).
    - If not cached, query Yahoo Finance for company info.
    - Clean up the name (remove suffixes).
    - Fallback to base ticker if no company name found.
    - Save results to cache for later use.

    Returns:
        CompanyMeta: Structured metadata for the given symbol.
    """
    cache = _load_cache()
    if symbol in cache:
        c = cache[symbol]
        return CompanyMeta(
            ticker=symbol,
            name=c.get("name"),
            raw_name=c.get("raw_name"),
            source=c.get("source", "cache"),
            base_ticker=c.get("base_ticker", _base_ticker(symbol))
        )

    info = _fetch_yf_info(symbol)
    raw_name = None
    source = "fallback"

    # Candidate fields from Yahoo Finance
    for key in ("longName", "shortName", "displayName"):
        val = info.get(key)
        if isinstance(val, str) and val.strip():
            raw_name = val.strip()
            source = f"info.{key}"
            break

    clean = _strip_legal_suffixes(raw_name) if raw_name else None

    # Fallback: just use base ticker
    if not clean:
        clean = _base_ticker(symbol)
        raw_name = clean
        source = "base_ticker"

    meta = CompanyMeta(
        ticker=symbol,
        name=clean,
        raw_name=raw_name,
        source=source,
        base_ticker=_base_ticker(symbol),
    )

    # Cache for future use
    cache[symbol] = {
        "name": meta.name,
        "raw_name": meta.raw_name,
        "source": meta.source,
        "base_ticker": meta.base_ticker,
    }
    _save_cache(cache)
    return meta


def auto_keywords(symbol: str) -> Tuple[str, list[str]]:
    """
    Generate a company search keyword set based on symbol.

    Returns:
        (company_name, required_keywords)

    Example:
        "AAPL" -> ("Apple", ["apple", "aapl"])
        "SAP.DE" -> ("SAP", ["sap", "sap.de", "sap"])
    """
    meta = get_company_meta(symbol)
    name = meta.name or meta.base_ticker

    # Prepare search keywords: company name (simplified) + ticker variations
    base = name.replace(",", " ").replace(".", " ")
    primary = base.split()[0] if base else meta.base_ticker
    req = sorted(set([primary.lower(), symbol.lower(), meta.base_ticker.lower()]))

    return name, req
