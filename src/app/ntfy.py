# src/app/ntfy.py
import requests
import logging

logger = logging.getLogger("stock-alerts")

def _mask_secret(s: str, keep: int = 1) -> str:
    if not s:
        return "(unset)"
    return s[:keep] + "…" + s[-keep:] if len(s) > keep * 2 else s[0] + "…" + s[-1]

def notify_ntfy(server: str, topic: str, title: str, message: str, dry_run: bool = False) -> None:
    if dry_run:
        logger.info("[DRY-RUN] %s | %s", title, message.replace("\n", " | "))
        return
    url = f"{server.rstrip('/')}/{topic}"
    headers = {"Title": title, "Priority": "high"}
    try:
        logger.info("Sende ntfy: title='%s', topic(masked)='%s'", title, _mask_secret(topic))
        r = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=20)
        r.raise_for_status()
        logger.debug("ntfy Response: %s", r.status_code)
    except requests.RequestException as e:
        logger.warning("ntfy-Senden fehlgeschlagen: %s", e)
