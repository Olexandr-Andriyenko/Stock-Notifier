# streamlit_app.py
import json
from pathlib import Path
import streamlit as st
import os, subprocess
from dotenv import load_dotenv

load_dotenv()
CONFIG_PATH = Path("config.json")

@st.cache_data
def load_config():
    return json.loads(CONFIG_PATH.read_text())

def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    

def commit_and_push(token: str | None = None) -> bool:
    """Commit config changes and push to GitHub."""
    token = token or os.environ.get("GH_TOKEN")
    if not token:
        st.error(
            "Bitte GitHub Token eingeben oder GH_TOKEN als Environment Variable setzen."
        )
        return False

    branch = "master"
    remote = f"https://{token}@github.com/Olexandr-Andriyenko/Stock-Notifier.git"

    try:
        subprocess.run(["git", "add", "config.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Update config via Streamlit"], check=True)
        subprocess.run(["git", "push", remote, branch], check=True)
    except subprocess.CalledProcessError as exc:
        st.error(f"Git push failed: {exc}")
        return False
    return True

cfg = load_config()

st.title("Konfiguration bearbeiten")
gh_token = st.sidebar.text_input("GitHub Token", type="password")

cfg["log"]["level"] = st.selectbox(
    "Log-Level",
    ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    index=["DEBUG","INFO","WARNING","ERROR","CRITICAL"].index(cfg["log"]["level"])
)

cfg["tickers"] = st.text_input(
    "Tickers (Komma getrennt)",
    ",".join(cfg["tickers"])
).split(",")

cfg["threshold_pct"] = st.number_input(
    "Schwellwert (%)",
    value=float(cfg["threshold_pct"]),
    step=0.1
)

if st.button("Speichern & Pushen"):
    save_config(cfg)
    if commit_and_push(gh_token):
        st.success("Gespeichert und ins Repo gepusht.")
