from services import analytics_service, data_loader
import pandas as pd
import threading
from infrastructure.messaging.telegram_provider import TelegramProvider

def format_report(df_full, target_date):
    """
    Formates a text report for Telegram based on the latest data.
    Includes insights and comparisons.
    """
    if df_full is None or df_full.empty:
        return "⚠️ Нет данных для отчета."

    # Ensure date format
    if not pd.api.types.is_datetime64_any_dtype(df_full['Дата_Отчета']):
         df_full['Дата_Отчета'] = pd.to_datetime(df_full['Дата_Отчета'])

    latest_date = df_full['Дата_Отчета'].max()
    
    # --- 1. DAILY STATS ---
    df_day = df_full[df_full['Дата_Отчета'] == latest_date]
    day_rev = df_day['Выручка с НДС'].sum()
    day_cost = df_day['Себестоимость'].sum()
    day_fc = (day_cost / day_rev * 100) if day_rev > 0 else 0

    # --- 2. MONTHLY STATS (Current vs Previous) ---
    # Current Month
    current_period = latest_date.to_period('M')
    df_full['Month_Year'] = df_full['Дата_Отчета'].dt.to_period('M')
    
    df_month = df_full[df_full['Month_Year'] == current_period]
    month_rev = df_month['Выручка с НДС'].sum()
    month_cost = df_month['Себестоимость'].sum()
    month_profit = month_rev - month_cost
    month_fc = (month_cost / month_rev * 100) if month_rev > 0 else 0
    
    # Previous Month (for insights)
    prev_period = current_period - 1
    df_prev = df_full[df_full['Month_Year'] == prev_period]
    prev_month_rev = df_prev['Выручка с НДС'].sum()

    # --- 3. INSIGHTS ---
    insights = analytics_service.calculate_insights(
        df_month, df_prev, month_rev, prev_month_rev, month_fc
    )
    
    insight_text = ""
    for note in insights:
        if note['level'] in ['error', 'warning', 'success', 'info']:
            # Filter all_good if we have real items? No, show all_good if nothing else
            if note['type'] == 'all_good' and len(insights) > 1: continue 
            insight_text += f"\n{note['message']}"

    # Top Dish of the Day
    try:
        top_dish_day = df_day.groupby('Блюдо')['Выручка с НДС'].sum().idxmax()
    except:
        top_dish_day = "-"

    month_name = data_loader.get_rus_month_name(latest_date.month)
    
    report = f"""
📊 **Отчет: Бар МЕСТО**
📅 {latest_date.strftime('%d.%m.%Y')}

🔹 **За {latest_date.strftime('%d.%m')} ({latest_date.strftime('%A')}):**
💰 Выручка: {int(day_rev):,} ₽
📉 Фуд-кост: {day_fc:.1f}%
🏆 Топ: {top_dish_day}

🔸 **За {month_name} ({latest_date.year}):**
💰 Выручка: {int(month_rev):,} ₽
📉 Фуд-кост: {month_fc:.1f}%
💸 Себестоимость: {int(month_cost):,} ₽
💵 Маржа: {int(month_profit):,} ₽

🔎 **Аналитика:**{insight_text}
    """
    return report.strip()

_messenger_provider = None

def get_messenger_provider() -> TelegramProvider:
    global _messenger_provider
    if _messenger_provider is None:
        _messenger_provider = TelegramProvider()
    return _messenger_provider

def send_telegram_message(token, chat_id, message):
    """
    Sends a text message to the specified Telegram chat.
    """
    return get_messenger_provider().send_message(token, chat_id, message)

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

    def background_send():
        for chat_id in ids:
            send_telegram_message(token, chat_id, message)

    t = threading.Thread(target=background_send, daemon=True)
    t.start()
    
    return True, f"✅ Отправка запущена в фоне ({len(ids)} чел.)"
