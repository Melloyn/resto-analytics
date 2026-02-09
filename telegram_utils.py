import requests
import pandas as pd

def format_report(df_full, target_date):
    """
    Formates a text report for Telegram based on the latest data.
    """
    if df_full is None or df_full.empty:
        return "⚠️ Нет данных для отчета."

    # Filter for the specific date (month) or take the latest
    # For simplicity, let's take the summary of the filtered view if possible, 
    # but since we don't have access to UI state here easily without passing it,
    # let's generate a general summary for the LATEST available month.
    
    latest_date = df_full['Дата_Отчета'].max()
    df_current = df_full[df_full['Дата_Отчета'] == latest_date]
    
    revenue = df_current['Выручка с НДС'].sum()
    cost = df_current['Себестоимость'].sum()
    profit = revenue - cost
    fc_percent = (cost / revenue * 100) if revenue > 0 else 0
    
    # Top Category
    top_cat = df_current.groupby('Категория')['Выручка с НДС'].sum().idxmax()
    
    report = f"""
📊 **Отчет: Бар МЕСТО**
📅 Дата: {latest_date.strftime('%d.%m.%Y')}

💰 **Выручка**: {int(revenue):,} ₽
📉 **Фуд-кост**: {fc_percent:.1f}%
💸 **Себестоимость**: {int(cost):,} ₽
💵 **Маржа**: {int(profit):,} ₽

🏆 **Топ категория**: {top_cat}
    """
    return report.strip()

def send_telegram_message(token, chat_id, message):
    """
    Sends a text message to the specified Telegram chat.
    """
    if not token or not chat_id:
        return False, "❌ Нет токена или Chat ID."

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True, "✅ Отчет отправлен!"
        else:
            return False, f"Ошибка Telegram: {response.text}"
    except Exception as e:
        return False, f"Ошибка сети: {str(e)}"
