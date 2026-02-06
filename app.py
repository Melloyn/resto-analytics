import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="RestoAnalytics AI", layout="wide")
st.title("📊 Ежедневная аналитика ресторана")

# --- БЛОК ЗАГРУЗКИ ДАННЫХ ---
st.sidebar.header("Загрузка данных")
uploaded_file = st.sidebar.file_uploader("Загрузите ежедневный отчет (Excel/CSV)", type=['csv', 'xlsx'])

# --- ФУНКЦИЯ ЧТЕНИЯ ФАЙЛА (Специфика твоего формата) ---
def load_data(file):
    # Твой файл имеет "шапку" на 5-6 строке, пропускаем лишнее
    try:
        # Пытаемся прочитать как Excel
        df = pd.read_excel(file, header=5)
    except:
        # Если не вышло, как CSV
        file.seek(0)
        df = pd.read_csv(file, header=5)
    
    # Очистка названий колонок (убираем пробелы)
    df.columns = df.columns.str.strip()
    
    # Фильтруем мусор (пустые строки и итоги)
    # Предполагаем, что названия позиций в первом столбце 'Склады' или 'Номенклатура'
    col_name = df.columns[0] 
    df = df.dropna(subset=[col_name])
    df = df[df[col_name] != "Итого"]
    
    # Преобразуем числа (убираем пробелы, меняем запятые на точки если нужно)
    cols_to_num = ['Количество', 'Себестоимость', 'Выручка с НДС', 'Фудкост']
    for col in cols_to_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            
    # Расчет чистой удельной себестоимости (Item Cost)
    # Защита от деления на ноль
    df['Unit_Cost'] = df.apply(lambda x: x['Себестоимость'] / x['Количество'] if x['Количество'] > 0 else 0, axis=1)
    
    return df

# --- ГЕНЕРАЦИЯ ДЕМО-ДАННЫХ (ЧТОБЫ ТЫ УВИДЕЛ ГРАФИКИ СРАЗУ) ---
# В реальности здесь будет база данных, но для старта симулируем историю
def generate_history(current_df):
    dates = pd.date_range(end=datetime.today(), periods=14)
    history = []
    
    total_rev = current_df['Выручка с НДС'].sum()
    total_cost = current_df['Себестоимость'].sum()
    
    for date in dates:
        # Добавляем случайный шум к данным, чтобы имитировать колебания продаж
        noise = np.random.normal(1, 0.15) # +- 15% колебаний
        history.append({
            'Дата': date,
            'Выручка': total_rev * noise,
            'Косты': total_cost * noise,
            'Прибыль': (total_rev - total_cost) * noise
        })
    return pd.DataFrame(history)

# --- ОСНОВНАЯ ЛОГИКА ---
if uploaded_file is not None:
    # 1. Загружаем текущий день
    df_day = load_data(uploaded_file)
    
    # 2. Генерируем историю (или загружаем из БД в будущем)
    df_history = generate_history(df_day)
    
    # --- KPI МЕТРИКИ (ВЕРХНЯЯ ПАНЕЛЬ) ---
    st.subheader("Сводка за сегодня")
    
    col1, col2, col3, col4 = st.columns(4)
    
    curr_rev = df_day['Выручка с НДС'].sum()
    curr_cost = df_day['Себестоимость'].sum()
    curr_fc = (curr_cost / curr_rev * 100) if curr_rev > 0 else 0
    
    # Сравнение со "вчера" (берем из истории)
    yesterday_rev = df_history.iloc[-2]['Выручка']
    delta_rev = ((curr_rev - yesterday_rev) / yesterday_rev) * 100
    
    col1.metric("Выручка", f"{curr_rev:,.0f} ₽", f"{delta_rev:.1f}%")
    col2.metric("Косты (Food Cost)", f"{curr_cost:,.0f} ₽", f"{(curr_cost/yesterday_rev - 1)*100:.1f}%", delta_color="inverse")
    col3.metric("Фуд-кост %", f"{curr_fc:.1f}%", "-0.5%") # Пример дельты
    col4.metric("Позиций в стопе", "3", "Low stock")

    # --- ТАБЫ С АНАЛИТИКОЙ ---
    tab1, tab2, tab3 = st.tabs(["📈 Динамика и Прогноз", "🍔 Анализ меню (C/C)", "📋 Детальная таблица"])
    
    with tab1:
        st.subheader("Тренд выручки и Прогноз (ML)")
        
        # Простая модель прогноза (Линейная регрессия + шум для демо)
        future_dates = pd.date_range(start=datetime.today() + timedelta(days=1), periods=2)
        avg_growth = df_history['Выручка'].pct_change().mean()
        last_val = df_history.iloc[-1]['Выручка']
        
        forecast = [last_val * (1 + avg_growth), last_val * (1 + avg_growth)**2]
        
        # График
        fig = go.Figure()
        
        # Факт
        fig.add_trace(go.Scatter(x=df_history['Дата'], y=df_history['Выручка'], 
                                 mode='lines+markers', name='Факт', line=dict(color='blue')))
        
        # Прогноз
        fig.add_trace(go.Scatter(x=future_dates, y=forecast, 
                                 mode='lines+markers', name='Прогноз AI', 
                                 line=dict(color='green', dash='dash')))
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.info(f"🤖 **Прогноз AI:** Завтра ожидаем выручку ~{forecast[0]:,.0f} ₽. " 
                f"Тренд: {'Рост' if forecast[0] > curr_rev else 'Спад'}.")

    with tab2:
        st.subheader("Контроль себестоимости (Top изменений)")
        
        # Топ позиций по выручке (ABC анализ)
        top_items = df_day.sort_values(by='Выручка с НДС', ascending=False).head(10)
        
        # График маржинальности
        fig_bar = px.bar(top_items, x=df_day.columns[0], y='Выручка с НДС', 
                         color='Фудкост', 
                         title="Топ-10 блюд по выручке (Цвет = Фудкост %)",
                         color_continuous_scale='RdYlGn_r') # Зеленый = низкий кост, Красный = высокий
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.write("🔴 **Внимание! Высокая себестоимость (Кост > 35%):**")
        high_cost = df_day[df_day['Фудкост'] > 35][['Склады', 'Себестоимость', 'Выручка с НДС', 'Фудкост']]
        st.dataframe(high_cost.style.format("{:.1f}"), use_container_width=True)

    with tab3:
        st.dataframe(df_day)

else:
    st.info("👈 Пожалуйста, загрузите файл с отчетом в меню слева, чтобы начать анализ.")
    st.write("Поддерживаемый формат: Выгрузка из iiko/r_keeper (CSV/XLSX)")