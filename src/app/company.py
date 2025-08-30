# src/app/company.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import json
import time
import yfinance as yf

CACHE_FILE = Path("company_cache.json")

# Übliche Rechtsform-Suffixe, die wir aus dem Namen entfernen
LEGAL_SUFFIXES = {
    "inc", "inc.", "corp", "corp.", "co", "co.", "ltd", "ltd.", "plc",
    "ag", "se", "nv", "sa", "oyj", "ab", "spa", "s.p.a.", "pte", "pteltd",
}

@dataclass
class CompanyMeta:
    ticker: str
    name: Optional[str]           # bereinigt, z.B. "Apple"
    raw_name: Optional[str]       # z.B. "Apple Inc."
    source: str                   # "info.longName", "info.shortName", "fallback"
    base_ticker: str              # z.B. "SAP" für "SAP.DE"

def _load_cache() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_cache(cache: Dict[str, Any]) -> None:
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

def _strip_legal_suffixes(name: str) -> str:
    parts = [p.strip(",. ").lower() for p in name.split()]
    # Entferne suffixe am Ende
    while parts and parts[-1] in LEGAL_SUFFIXES:
        parts.pop()
    if not parts:
        return name.strip()
    # Erste Buchstaben groß
    cleaned = " ".join(parts)
    return cleaned.title()

def _base_ticker(symbol: str) -> str:
    # "SAP.DE" -> "SAP"; "BRK.B" -> "BRK"; "^GDAXI" -> "^GDAXI" (Indices lassen wir wie sie sind)
    if symbol.startswith("^"):
        return symbol
    if "." in symbol:
        return symbol.split(".", 1)[0]
    return symbol

def _fetch_yf_info(symbol: str, retries: int = 2, delay: float = 0.4) -> Dict[str, Any]:
    last_exc = None
    for _ in range(retries + 1):
        try:
            t = yf.Ticker(symbol)
            # yfinance: get_info ist oft stabiler als .info (je nach Version)
            info = t.get_info() if hasattr(t, "get_info") else getattr(t, "info", {})
            if info:
                return info
        except Exception as e:
            last_exc = e
            time.sleep(delay)
    return {}

def get_company_meta(symbol: str) -> CompanyMeta:
    """Ermittelt Firmenname & Basis-Ticker, mit Cache & Fallbacks."""
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

    # Kandidaten in Reihenfolge
    for key in ("longName", "shortName", "displayName"):
        val = info.get(key)
        if isinstance(val, str) and val.strip():
            raw_name = val.strip()
            source = f"info.{key}"
            break

    # Bereinigung
    clean = None
    if raw_name:
        clean = _strip_legal_suffixes(raw_name)

    # Wenn gar nichts: versuche Basis-Ticker als Name
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

    # Cache speichern
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
    Liefert (firmenname_oder_ticker, required_keywords_lower)
    - company: z.B. "Apple"
    - keywords: ["apple", "aapl"]
    """
    meta = get_company_meta(symbol)
    name = meta.name or meta.base_ticker
    # Keywords: Firmenname (ohne Sonderzeichen grob) & Ticker lower
    base = name.replace(",", " ").replace(".", " ")
    primary = base.split()[0] if base else meta.base_ticker
    req = sorted(set([primary.lower(), symbol.lower(), meta.base_ticker.lower()]))
    return name, req
