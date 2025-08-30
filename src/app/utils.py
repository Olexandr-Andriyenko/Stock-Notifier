def mask_secret(s: str, keep: int = 1) -> str:
    """Maskiert sensible Strings für Logging-Ausgaben."""
    if not s:
        return "(unset)"
    return s[:keep] + "…" + s[-keep:] if len(s) > keep * 2 else s[0] + "…" + s[-1]