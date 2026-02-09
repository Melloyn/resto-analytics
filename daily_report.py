import os
import pandas as pd
from datetime import datetime
import telegram_utils
import toml

# Load secrets (local specific, on server we will use env vars)
try:
    secrets = toml.load(".streamlit/secrets.toml")
    TOKEN = secrets["TELEGRAM_TOKEN"]
    CHAT_ID = secrets["TELEGRAM_CHAT_ID"]
except:
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_daily_report():
    print(f"🚀 Starting report generation at {datetime.now()}")
    
    # 1. Load Data (Parquet for speed)
    if os.path.exists("data_cache.parquet"):
        df = pd.read_parquet("data_cache.parquet")
    else:
        # Fallback or try to load excel if parquet missing
        try:
             # Logic to load raw Excel if needed (simplified here)
             # In production, we assume data is cached or loaded fresh
             print("⚠️ Parquet not found. Please run app to cache data.")
             return
        except:
            return

    # 2. Format Report
    report = telegram_utils.format_report(df, datetime.now())

    # 3. Send
    success, msg = telegram_utils.send_telegram_message(TOKEN, CHAT_ID, report)
    print(msg)

if __name__ == "__main__":
    send_daily_report()
