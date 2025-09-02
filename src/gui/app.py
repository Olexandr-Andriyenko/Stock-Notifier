# streamlit_app.py
import json
from pathlib import Path
import streamlit as st
import os, subprocess

CONFIG_PATH = Path("config.json")

@st.cache_data
def load_config():
    return json.loads(CONFIG_PATH.read_text())

def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    

def commit_and_push():
    token = os.environ["GH_TOKEN"]
    repo = "https://github.com/Olexandr-Andriyenko/Stock-Notifier.git"      
    branch = "master"                            

    subprocess.run(["git", "add", "config.json"], check=True)
    subprocess.run(["git", "commit", "-m", "Update config via Streamlit"], check=True)
    remote = f"https://{token}@{repo}"
    subprocess.run(["git", "push", remote, branch], check=True)

cfg = load_config()

st.title("Konfiguration bearbeiten")

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
    commit_and_push()
    st.success("Gespeichert und ins Repo gepusht.")
