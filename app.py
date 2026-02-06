import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import re
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="RestoAnalytics: Место", layout="wide")
st.title("📊 Аналитика: Бар МЕСТО")

# --- ИНИЦИАЛИЗАЦИЯ ПАМЯТИ ---
if 'df_full' not in st.session_state:
    st.session_state.df_full = None

# --- ФУНКЦИИ ---
RUS_MONTHS = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6,
    'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
    'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
    'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12
}

def parse_russian_date(text):
    text = text.lower()
    match_text = re.search(r'(\d{1,2})\s+([а-я]+)\s+(\d{4})', text)
    if match_text:
        day, month_str, year = match_text.groups()
        if month_str in RUS_MONTHS:
            return datetime(int(year), RUS_MONTHS[month_str], int(day))
    match_digit = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    if match_digit:
        return datetime.strptime(match_digit.group(0), '%d.%m.%Y')
    return None

def process_single_file(file_content, filename=""):
    try:
        if isinstance(file_content, BytesIO): file_content.seek(0)
        try:
            df_raw = pd.read_csv(file_content, header=None, nrows=10, sep=None, engine='python')
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df_raw = pd.read_excel(file_content, header=None, nrows=10)

        header_text = " ".join(df_raw.iloc[0:10, 0].astype(str).tolist())
        report_date = parse_russian_date(header_text)
        
        if not report_date:
            for rus, eng in [('feb', 'февраля'), ('jan', 'января'), ('mar', 'марта')]:
                if rus in filename.lower():
                     d_match = re.search(r'(\d{1,2})', filename)
                     if d_match:
                         report_date = datetime(2026, RUS_MONTHS[eng], int(d_match.group(1)))
                         break
        if not report_date: report_date = datetime.now()

        if isinstance(file_content, BytesIO): file_content.seek(0)
        try:
            df = pd.read_csv(file_content, header=5, sep=None, engine='python')
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df = pd.read_excel(file_content, header=5)

        df.columns = df.columns.str.strip()
        if 'Выручка с НДС' not in df.columns: return None

        col_name = df.columns[0] # Имя позиции
        df = df.dropna(subset=[col_name])
        df = df[~df[col_name].astype(str).str.contains("Итого", case=False)]
        
        cols_to_num = ['Количество', 'Себестоимость', 'Выручка с НДС']
        for col in cols_to_num:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # === ВАЖНО: Считаем цену за единицу (Unit Cost) ===
        # Unit_Cost = Себестоимость / Количество
        df['Unit_Cost'] = df.apply(lambda x: (x['Себестоимость'] / x['Количество']) if x['Количество'] != 0 else 0, axis=1)
        
        df['Фудкост'] = df.apply(lambda x: (x['Себестоимость'] / x['Выручка с НДС'] * 100) if x['Выручка с НДС'] > 0 else 0, axis=1)
        df['Дата_Отчета'] = report_date
        
        # Переименуем колонку с названием блюда для удобства
        df = df.rename(columns={col_name: 'Блюдо'})
        
        return df
    except Exception:
        return None

def load_all_from_yandex(folder_path):
    token = st.secrets.get("YANDEX_TOKEN")
    if not token:
        st.error("⚠️ Нет YANDEX_TOKEN в Secrets!")
        return []
    
    headers = {'Authorization': f'OAuth {token}'}
    api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
    params = {'path': folder_path, 'limit': 100}
    
    try:
        response = requests.get(api_url, headers=headers, params=params)
        if response.status_code != 200:
            st.error(f"Ошибка Яндекс.Диска: {response.status_code}")
            return []
            
        items = response.json().get('_embedded', {}).get('items', [])
        files = [i for i in items if i['type'] == 'file']
        
        data_frames = []
        progress_bar = st.progress(0)
        
        for idx, item in enumerate(files):
            file_resp = requests.get(item['file'], headers=headers)
            df = process_single_file(BytesIO(file_resp.content), filename=item['name'])
            if df is not None:
                data_frames.append(df)
            progress_bar.progress((idx + 1) / len(files))
            
        progress_bar.empty()
        return data_frames
    except Exception as e:
        st.error(f"Ошибка: {e}")
        return []

# --- ИНТЕРФЕЙС ЗАГРУЗКИ ---
st.sidebar.header("📂 Управление данными")
source_mode = st.sidebar.radio("Источник:", ["Яндекс.Диск", "Ручная загрузка"])

if source_mode == "Ручная загрузка":
    uploaded_files = st.sidebar.file_uploader("Файлы", accept_multiple_files=True)
    if uploaded_files:
        temp_data = []
        for f in uploaded_files:
            df = process_single_file(f, f.name)
            if df is not None: temp_data.append(df)
        if temp_data:
            st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')

elif source_mode == "Яндекс.Диск":
    yandex_path = st.sidebar.text_input("Папка:", "Отчеты_Ресторан")
    if st.sidebar.button("🔄 Скачать и Запомнить"):
        with st.spinner("Загрузка с Яндекса..."):
            temp_data = load_all_from_yandex(yandex_path)
            if temp_data:
                st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')
                st.success(f"Загружено файлов: {len(temp_data)}")

# --- АНАЛИТИКА ---
if st.session_state.df_full is not None:
    df_full = st.session_state.df_full
    
    dates_list = sorted(df_full['Дата_Отчета'].unique(), reverse=True)
    date_str_list = [d.strftime('%d.%m.%Y') for d in dates_list]
    date_options = ["📅 ИТОГИ (Весь период)"] + date_str_list
    
    st.write("---")
    col_sel1, col_sel2 = st.columns([1, 4])
    selected_option = col_sel1.selectbox("📅 Выберите период:", date_options)
    
    # ==========================
    #      РЕЖИМ: ИТОГИ
    # ==========================
    if "ИТОГИ" in selected_option:
        st.subheader(f"📈 Сводка за {len(dates_list)} дн.")
        
        # Основные KPI
        total_rev = df_full['Выручка с НДС'].sum()
        total_cost = df_full['Себестоимость'].sum()
        avg_fc = (total_cost / total_rev * 100) if total_rev > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Выручка Total", f"{total_rev:,.0f} ₽")
        m2.metric("Себестоимость", f"{total_cost:,.0f} ₽")
        m3.metric("Фуд-кост %", f"{avg_fc:.1f}%")
        
        # Табы для итогов
        tab_main, tab_price_change = st.tabs(["📊 Топ продаж", "📉 Изменение закупочных цен (NEW)"])
        
        with tab_main:
            df_items = df_full.groupby('Блюдо')[['Выручка с НДС', 'Себестоимость']].sum().reset_index()
            df_items['Фудкост'] = df_items['Себестоимость'] / df_items['Выручка с НДС'] * 100
            top_items = df_items.sort_values('Выручка с НДС', ascending=False).head(10)
            st.plotly_chart(px.bar(top_items, x='Блюдо', y='Выручка с НДС', 
                            color='Фудкост', color_continuous_scale='RdYlGn_r', title="Топ продаж за всё время"), use_container_width=True)
        
        # === НОВАЯ ВКЛАДКА: АНАЛИЗ ИЗМЕНЕНИЯ ЦЕН ===
        with tab_price_change:
            st.write("Здесь мы сравниваем **цену за единицу (Unit Cost)** в первый и последний день продаж за этот период.")
            
            # 1. Группируем по Блюду и Дате, берем средний Unit_Cost за день (на случай дублей)
            price_history = df_full.groupby(['Блюдо', 'Дата_Отчета'])['Unit_Cost'].mean().reset_index()
            
            # 2. Находим первую и последнюю цену для каждого блюда
            price_analysis = []
            
            # Получаем список уникальных блюд
            unique_items = price_history['Блюдо'].unique()
            
            for item in unique_items:
                item_data = price_history[price_history['Блюдо'] == item].sort_values('Дата_Отчета')
                if len(item_data) > 1: # Нужна хотя бы пара дней для сравнения
                    first_price = item_data.iloc[0]['Unit_Cost']
                    last_price = item_data.iloc[-1]['Unit_Cost']
                    
                    # Считаем разницу, если цена значимая
                    if first_price > 1: 
                        diff_pct = ((last_price - first_price) / first_price) * 100
                        diff_abs = last_price - first_price
                        
                        # Добавляем в список, если изменение больше 1% (чтобы убрать шум)
                        if abs(diff_pct) > 1:
                            price_analysis.append({
                                'Блюдо': item,
                                'Старая цена': first_price,
                                'Новая цена': last_price,
                                'Рост (руб)': diff_abs,
                                'Рост (%)': diff_pct
                            })
            
            if price_analysis:
                df_changes = pd.DataFrame(price_analysis)
                
                # Сортируем: сверху те, что подорожали сильнее всего
                df_changes = df_changes.sort_values('Рост (%)', ascending=False)
                
                # Красим таблицу
                def color_change(val):
                    color = 'red' if val > 0 else 'green'
                    return f'color: {color}'
                
                st.dataframe(df_changes.style.format({
                    'Старая цена': "{:.1f} ₽",
                    'Новая цена': "{:.1f} ₽",
                    'Рост (руб)': "{:+.1f} ₽",
                    'Рост (%)': "{:+.1f}%"
                }).applymap(color_change, subset=['Рост (%)', 'Рост (руб)']), use_container_width=True, height=500)
            else:
                st.success("Цены закупки стабильны! Существенных изменений не найдено.")

    # ==========================
    #      РЕЖИМ: ДЕНЬ
    # ==========================
    else:
        current_date = datetime.strptime(selected_option, '%d.%m.%Y')
        df_day = df_full[df_full['Дата_Отчета'] == current_date]
        
        day_rev = df_day['Выручка с НДС'].sum()
        day_cost = df_day['Себестоимость'].sum()
        
        # Сравнение с прошлым днем
        delta_msg = "нет данных"
        try:
            curr_idx = date_str_list.index(selected_option)
            if curr_idx + 1 < len(dates_list):
                prev_date = dates_list[curr_idx + 1]
                prev_rev = df_full[df_full['Дата_Отчета'] == prev_date]['Выручка с НДС'].sum()
                if prev_rev > 0:
                    diff = ((day_rev - prev_rev) / prev_rev) * 100
                    delta_msg = f"{diff:+.1f}%"
        except: pass

        st.subheader(f"Отчет за {current_date.strftime('%d.%m')}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Выручка", f"{day_rev:,.0f} ₽", delta_msg)
        m2.metric("Фуд-кост", f"{(day_cost/day_rev*100):.1f}%")
        m3.metric("Чеков", len(df_day))

        # --- ЗОНА РИСКА (>25%) ---
        st.write("---")
        with st.expander("⚠️ **ЗОНА РИСКА: Фуд-кост выше 25%**", expanded=True):
            high_cost_df = df_day[df_day['Фудкост'] > 25].sort_values(by='Фудкост', ascending=False)
            if not high_cost_df.empty:
                display_df = high_cost_df[['Блюдо', 'Себестоимость', 'Выручка с НДС', 'Фудкост']]
                st.dataframe(display_df.style.format({
                    'Себестоимость': "{:.1f}", 'Выручка с НДС': "{:.1f}", 'Фудкост': "{:.1f}%"
                }).background_gradient(subset=['Фудкост'], cmap='Reds', vmin=25, vmax=50), use_container_width=True)
            else:
                st.success("Нет позиций с костом выше 25%.")

        tab1, tab2 = st.tabs(["📊 Меню", "🔮 Прогноз"])
        with tab1:
            st.plotly_chart(px.bar(df_day.sort_values('Выручка с НДС', ascending=False).head(10), 
                            x='Блюдо', y='Выручка с НДС', 
                            color='Фудкост', color_continuous_scale='RdYlGn_r'), use_container_width=True)
        with tab2:
            st.info("Прогноз на 2 дня вперед")
            daily_grp = df_full.groupby('Дата_Отчета')['Выручка с НДС'].sum().reset_index()
            last_3_avg = daily_grp['Выручка с НДС'].tail(3).mean()
            if pd.isna(last_3_avg): last_3_avg = day_rev
            future_days = [daily_grp['Дата_Отчета'].max() + timedelta(days=i) for i in range(1, 3)]
            future_vals = [last_3_avg * 1.0, last_3_avg * 1.05]
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=daily_grp['Дата_Отчета'], y=daily_grp['Выручка с НДС'],
                                           mode='lines+markers', name='Факт', line=dict(color='blue')))
            fig_trend.add_trace(go.Scatter(x=future_days, y=future_vals,
                                           mode='lines+markers', name='Прогноз', line=dict(color='green', dash='dash')))
            st.plotly_chart(fig_trend, use_container_width=True)

else:
    st.info("👈 Нажмите 'Скачать' или загрузите файлы.")
