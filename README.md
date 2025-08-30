# 📈 Stock Notifier – Push Alerts for Stock Movements

> **Short Description:**  
> This project monitors selected stock prices using [Yahoo Finance](https://pypi.org/project/yfinance/).  
> If a stock moves more than a defined percentage from the opening price, you will receive a **push notification** on your phone via [ntfy.sh](https://ntfy.sh/).  

---

## 🚀 Features

- **Automated stock monitoring**  
  Checks defined tickers (e.g. `AAPL`, `SAP.DE`) at regular intervals.
- **Push alerts via ntfy**  
  Delivered directly as push notifications to your smartphone (Android, iOS, or desktop browser).
- **Configurable threshold**  
  Notifications only if the price change is e.g. > ±3%.
- **Market hours filter**  
  Alerts only during configurable trading hours (default: Mon–Fri, 08:00–22:00 Berlin time).
- **Anti-spam state**  
  Prevents repeated alerts: a new alert is only sent once the price returns inside the corridor (< threshold).
- **Logging**  
  Configurable log level (`DEBUG`/`INFO`/`WARNING`…), optional rotating log file.
- **Test mode**  
  Easily test without real price data or actual pushes (`dry_run`, `force_delta_pct`).

---

## 🗂 Project Structure

```bash
└── 📁stoock_notifier
        └── 📁src
        └── 📁app
            ├── __init__.py
            ├── config.py
            ├── core.py
            ├── logging_setup.py
            ├── market.py
            ├── ntfy.py
            ├── state.py
    ├── .env
    ├── .gitignore
    ├── config.json
    ├── main.py
    ├── README.md
    └── requirements.txt
```

## ⚙️ Requirements

- Python **3.10+**
- Internet connection (for yfinance + ntfy)
- ntfy app on your smartphone or desktop  
  - Android: [Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy)  
  - iOS: [App Store](https://apps.apple.com/us/app/ntfy/id1625396347)  
  - Desktop: [Web Client](https://ntfy.sh/app)

---

## 🔧 Installation

1. **Clone or download the repository**

   ```bash
   git clone https://github.com/your-user/stock-notifier.git
   cd stock-notifier
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   # Linux:
   source .venv/bin/activate 
   # Windows: 
   .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

## 📝 Configuration

1. **Sensitive data**
   - Create a `.env` file in the project root:

      ```env
      # ntfy settings (Secret!):
      NTFY_TOPIC=dein-geheimes-topic
      NTFY_SERVER=https://ntfy.sh

      # Optional: Override log level
      LOG_LEVEL=DEBUG
      ```

2. **Project settings**
   - Example for `config.json:`:

      ```json
      {
      "tickers": ["AAPL", "SAP.DE"],
      "threshold_pct": 3.0,
      "log": {
         "level": "INFO",
         "to_file": true,
         "file_path": "alerts.log",
         "file_max_bytes": 1000000,
         "file_backup_count": 3
      },
      "market_hours": {
         "enabled": true,
         "tz": "Europe/Berlin",
         "start_hour": 8,
         "end_hour": 22,
         "days_mon_to_fri_only": true
      },
      "test": {
         "enabled": false,
         "bypass_market_hours": true,
         "force_delta_pct": null,
         "dry_run": false
      },
      "state_file": "alert_state.json"
      }
      ```

## ▶️ Usage

- Start the notifier:
  
  ```bash
   python main.py
  ```

- Example log output:

   ```bash
   2025-08-30 08:41:01 INFO Job start (2025-08-30 08:41:01), Ticker=AAPL,SAP.DE, Schwelle=±3.0%
   2025-08-30 08:41:01 INFO Handelszeit? True (effective=True)
   2025-08-30 08:41:02 INFO AAPL | Last=232.27 Open=232.56 Δ=-0.12%
   2025-08-30 08:41:02 INFO SAP.DE | Last=120.12 Open=116.00 Δ=+3.55%
   2025-08-30 08:41:02 INFO State-Wechsel (SAP.DE): none → up. Sende Alert.
   2025-08-30 08:41:02 INFO Sende ntfy: title='Stock Alert: SAP.DE', topic(masked)='7gl6…0KEz'
   ```

- On your smartphone you will see e.g.:

  ```bash
   📈 SAP.DE: +3.55% vs. Eröffnung
   Aktuell: 120.12 | Open: 116.00
  ```

## 🧪 Test Mode

Safe testing without real notifications:

```json
"test": {
  "enabled": true,
  "bypass_market_hours": true,
  "force_delta_pct": 4.2,
  "dry_run": true
}
```

- `force_delta_pct`: Simulates a price change (e.g. +4.2%).
- `dry_run: true`: No push to ntfy, only log output.
