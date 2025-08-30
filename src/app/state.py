# src/app/state.py
import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger("stock-alerts")


def load_state(path: Path) -> Dict[str, str]:
    """
    Load the last alert "state" from a JSON file.

    The state keeps track of which direction (up/down/none) a stock
    has already triggered an alert for. This prevents sending duplicate
    notifications every run.

    Args:
        path (Path): Path to the JSON state file.

    Returns:
        Dict[str, str]: Mapping {ticker: "up" | "down" | "none"}.
                        Empty dict if file does not exist or cannot be parsed.

    Example:
        >>> load_state(Path("alert_state.json"))
        {'AAPL': 'up', 'SAP.DE': 'none'}
    """
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            logger.debug("Loaded state: %s", data)
            return data
        except Exception as e:
            logger.warning("Could not load state (%s). Starting fresh with empty dict.", e)
            return {}
    return {}


def save_state(path: Path, state: Dict[str, str]) -> None:
    """
    Save the current alert state to disk.

    Args:
        path (Path): Path to the JSON state file.
        state (Dict[str, str]): Mapping {ticker: "up" | "down" | "none"}.

    Returns:
        None

    Side effects:
        - Overwrites the JSON state file with updated ticker states.

    Example:
        >>> save_state(Path("alert_state.json"), {'AAPL': 'up'})
    """
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.debug("Saved state: %s", state)
