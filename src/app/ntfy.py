import requests
import logging
from src.app.utils import mask_secret

logger = logging.getLogger("stock-alerts")

def notify_ntfy(
    server: str,
    topic: str,
    title: str,
    message: str,
    *,
    dry_run: bool = False,
    markdown: bool = False,
    click_url: str | None = None,
) -> None:
    """
    Send a push notification via ntfy.sh.

    Args:
        server (str): ntfy server URL (e.g. "https://ntfy.sh").
        topic (str): Secret topic string subscribed in the ntfy app.
        title (str): Notification title (header).
        message (str): Notification body text (supports Unicode + Emojis).
        dry_run (bool, optional): If True, do not actually send,
                                  only log message content. Default: False.
        markdown (bool, optional): If True, enable Markdown rendering
                                   in ntfy (web app only for now).
                                   Default: False.
        click_url (str | None, optional): Optional URL that opens when
                                          tapping the notification.

    Returns:
        None

    Side effects:
        - Performs an HTTP POST request to the ntfy server.
        - On success, the subscribed app receives a push message.

    Example:
        >>> notify_ntfy(
                "https://ntfy.sh",
                "my-secret-topic",
                "Stock Alert",
                "AAPL is up 5% 📈",
                markdown=True,
                click_url="https://finance.yahoo.com/quote/AAPL"
            )
    """
    if dry_run:
        logger.info("[DRY-RUN] %s | %s", title, message.replace("\n", " | "))
        return

    # ntfy expects messages via HTTP POST to the topic URL
    url = f"{server.rstrip('/')}/{topic}"
    headers = {
        "Title": title,
        "Priority": "high",  # high = more prominent push (can be tuned)
    }

    if markdown:
        # Enable Markdown formatting (bold, italic, links, lists, etc.)
        headers["Markdown"] = "yes"
        # Alternative would be: Content-Type: text/markdown

    if click_url:
        # When the user taps the notification in the app/web,
        # this URL will be opened.
        headers["Click"] = click_url

    try:
        logger.info("Sending ntfy: title='%s', topic(masked)='%s'", title, mask_secret(topic))
        r = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=20)
        r.raise_for_status()
        logger.debug("ntfy Response: %s", r.status_code)
    except requests.RequestException as e:
        logger.warning("ntfy send failed: %s", e)
