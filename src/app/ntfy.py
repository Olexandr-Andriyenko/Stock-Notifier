# src/app/ntfy.py
import requests
import logging

logger = logging.getLogger("stock-alerts")

def _mask(s: str, keep: int = 1) -> str:
    if not s:
        return "(unset)"
    return s[:keep] + "…" + s[-keep:] if len(s) > keep*2 else s[0] + "…" + s[-1]

def notify_ntfy(server: str, topic: str, title: str, message: str,
                *, dry_run: bool = False, markdown: bool = False, click_url: str | None = None) -> None:
    """
    Sendet eine ntfy Nachricht.
    - markdown=True => rendert Markdown (Web-App; siehe Doku)
    - click_url     => URL wird beim Tippen auf die Benachrichtigung geöffnet
    """
    if dry_run:
        logger.info("[DRY-RUN] %s | %s", title, message.replace("\n", " | "))
        return

    url = f"{server.rstrip('/')}/{topic}"
    headers = {"Title": title, "Priority": "high"}
    if markdown:
        # Variante A: explizit aktivieren
        headers["Markdown"] = "yes"     # alias: X-Markdown / md
        # Alternative wäre: Content-Type: text/markdown setzen

    if click_url:
        headers["Click"] = click_url    # Beim Tippen öffnen (Web/App)

    try:
        logger.info("Sende ntfy: title='%s', topic(masked)='%s'", title, _mask(topic))
        r = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=20)
        r.raise_for_status()
        logger.debug("ntfy Response: %s", r.status_code)
    except requests.RequestException as e:
        logger.warning("ntfy-Senden fehlgeschlagen: %s", e)
