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
    
    # --- 1. DAILY STATS ---
    df_day = df_full[df_full['Дата_Отчета'] == latest_date]
    day_rev = df_day['Выручка с НДС'].sum()
    day_cost = df_day['Себестоимость'].sum()
    day_profit = day_rev - day_cost
    day_fc = (day_cost / day_rev * 100) if day_rev > 0 else 0

    # --- 2. MONTHLY STATS (Cumulative) ---
    # Filter from 1st day of the month of the latest_date
    start_of_month = latest_date.replace(day=1)
    df_month = df_full[(df_full['Дата_Отчета'] >= start_of_month) & (df_full['Дата_Отчета'] <= latest_date)]
    
    month_rev = df_month['Выручка с НДС'].sum()
    month_cost = df_month['Себестоимость'].sum()
    month_profit = month_rev - month_cost
    month_fc = (month_cost / month_rev * 100) if month_rev > 0 else 0

    # Top Dish of the Day
    try:
        top_dish_day = df_day.groupby('Блюдо')['Выручка с НДС'].sum().idxmax()
    except:
        top_dish_day = "-"

    report = f"""
📊 **Отчет: Бар МЕСТО**
📅 {latest_date.strftime('%d.%m.%Y')}

🔹 **За день (Day):**
💰 Выручка: {int(day_rev):,} ₽
📉 Фуд-кост: {day_fc:.1f}%
🏆 Топ: {top_dish_day}

🔸 **За месяц (Month):**
💰 Выручка: {int(month_rev):,} ₽
📉 Фуд-кост: {month_fc:.1f}%
💸 Себестоимость: {int(month_cost):,} ₽
💵 Маржа: {int(month_profit):,} ₽
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

def send_to_all(token, chat_ids_raw, message):
    """
    Sends message to multiple users (comma separated string of IDs).
    """
    if not chat_ids_raw:
        return False, "❌ Нет Chat ID."
    
    # Split by comma and clean up
    ids = [id.strip() for id in str(chat_ids_raw).split(',') if id.strip()]
    
    if not ids:
        return False, "❌ Список ID пуст."

    success_count = 0
    errors = []

    for chat_id in ids:
        ok, msg = send_telegram_message(token, chat_id, message)
        if ok:
            success_count += 1
        else:
            errors.append(msg)
    
    if success_count == len(ids):
        return True, f"✅ Отправлено всем ({success_count} чел.)"
    elif success_count > 0:
        return True, f"⚠️ Отправлено {success_count} из {len(ids)}. Ошибки: {'; '.join(errors)}"
    else:
        return False, f"❌ Ошибка отправки: {'; '.join(errors)}"
