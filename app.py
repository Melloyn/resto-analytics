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
st.set_page_config(page_title="RestoAnalytics: Место", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Аналитика: Бар МЕСТО")

# --- СЛОВАРЬ РУССКИХ МЕСЯЦЕВ ---
RUS_MONTHS = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6,
    'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
    'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
    'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12
}

# --- УМНЫЙ ПАРСЕР ДАТ ---
def parse_russian_date(text):
    text = text.lower()
    # 1. Пробуем формат "1 февраля 2026"
    match_text = re.search(r'(\d{1,2})\s+([а-я]+)\s+(\d{4})', text)
    if match_text:
        day, month_str, year = match_text.groups()
        if month_str in RUS_MONTHS:
            return datetime(int(year), RUS_MONTHS[month_str], int(day))
    
    # 2. Пробуем формат "01.02.2026"
    match_digit = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    if match_digit:
        return datetime.strptime(match_digit.group(0), '%d.%m.%Y')
        
    return None

def process_single_file(file_content, filename=""):
    try:
        # Сброс указателя файла
        if isinstance(file_content, BytesIO): file_content.seek(0)
        
        # 1. Читаем заголовок (первые 10 строк) чтобы найти дату
        try:
            df_raw = pd.read_csv(file_content, header=None, nrows=10, sep=None, engine='python')
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df_raw = pd.read_excel(file_content, header=None, nrows=10)

        # Ищем дату в заголовке файла
        header_text = " ".join(df_raw.iloc[0:10, 0].astype(str).tolist())
        report_date = parse_russian_date(header_text)
        
        # Если в файле даты нет, ищем в названии файла (например "1 feb.xlsx")
        if not report_date:
            # Простой поиск цифры дня в названии, если там есть месяц (например "1 feb")
            for rus, eng in [('feb', 'февраля'), ('jan', 'января'), ('mar', 'марта')]: # Можно расширить
                if rus in filename.lower():
                     # Пытаемся найти день
                     d_match = re.search(r'(\d{1,2})', filename)
                     if d_match:
                         # ХАК: Пока считаем год 2026, если не указан
                         report_date = datetime(2026, RUS_MONTHS[eng], int(d_match.group(1)))
                         break
        
        # Если совсем не нашли — ставим сегодня (чтобы не падало)
        if not report_date: 
            report_date = datetime.now()

        # 2. Читаем основную таблицу (твоя структура: заголовок на 6-й строке Excel, индекс 5)
        if isinstance(file_content, BytesIO): file_content.seek(0)
        try:
            df = pd.read_csv(file_content, header=5, sep=None, engine='python')
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df = pd.read_excel(file_content, header=5)

        # Очистка названий колонок
        df.columns = df.columns.str.strip()
        
        # Проверка структуры
        if 'Выручка с НДС' not in df.columns:
            return None # Это не тот файл

        # Убираем строки "Итого" и пустые
        col_name = df.columns[0] # "Склады"
        df = df.dropna(subset=[col_name])
        df = df[~df[col_name].astype(str).str.contains("Итого", case=False)]
        
        # Конвертация чисел
        cols_to_num = ['Количество', 'Себестоимость', 'Выручка с НДС']
        for col in cols_to_num:
            if col in df.columns:
                # Убираем пробелы (1 000 -> 1000) и меняем запятые
                df[col] = df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Считаем Фудкост сами (чтобы было точно)
        df['Фудкост'] = df.apply(lambda x: (x['Себестоимость'] / x['Выручка с НДС'] * 100) if x['Выручка с НДС'] > 0 else 0, axis=1)
        
        df['Дата_Отчета'] = report_date
        return df

    except Exception as e:
        # st.error(f"Ошибка чтения {filename}: {e}")
        return None

def load_all_from_yandex(folder_path):
    token = st.secrets.get("YANDEX_TOKEN")
    if not token:
        st.error("⚠️ Не найден YANDEX_TOKEN в настройках (Secrets).")
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
        st.error(f"Ошибка подключения: {e}")
        return []

# --- ИНТЕРФЕЙС ---
st.sidebar.header("📂 Источник данных")
source_mode = st.sidebar.radio("Режим работы:", ["Ручная загрузка (Тест)", "Яндекс.Диск (Авто)"])

all_data = []

if source_mode == "Ручная загрузка (Тест)":
    uploaded_files = st.sidebar.file_uploader("Загрузите ежедневные отчеты", accept_multiple_files=True)
    if uploaded_files:
        for f in uploaded_files:
            df = process_single_file(f, f.name)
            if df is not None: all_data.append(df)
            
elif source_mode == "Яндекс.Диск (Авто)":
    yandex_path = st.sidebar.text_input("Папка на Диске:", "/Отчеты_Ресторан")
    if st.sidebar.button("🔄 Обновить данные"):
        with st.spinner("Скачиваем отчеты..."):
            all_data = load_all_from_yandex(yandex_path)

# --- ОСНОВНАЯ ЛОГИКА ---
if all_data:
    # Собираем все дни в одну таблицу
    df_full = pd.concat(all_data, ignore_index=True)
    df_full = df_full.sort_values(by='Дата_Отчета')
    
    # Список дат для меню
    dates_list = sorted(df_full['Дата_Отчета'].unique(), reverse=True)
    date_options = ["📅 ИТОГИ (Весь период)"] + [d.strftime('%d.%m.%Y') for d in dates_list]
    
    st.write("---")
    # Селектор даты
    col_sel1, col_sel2 = st.columns([1, 4])
    selected_option = col_sel1.selectbox("📅 Выберите период:", date_options)
    
    # ---------------- РЕЖИМ: ИТОГИ ----------------
    if "ИТОГИ" in selected_option:
        st.subheader(f"📈 Сводка за {len(dates_list)} дн.")
        
        # Суммируем всё
        total_rev = df_full['Выручка с НДС'].sum()
        total_cost = df_full['Себестоимость'].sum()
        avg_fc = (total_cost / total_rev * 100) if total_rev > 0 else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Выручка Total", f"{total_rev:,.0f} ₽")
        m2.metric("Себестоимость", f"{total_cost:,.0f} ₽")
        m3.metric("Фуд-кост %", f"{avg_fc:.1f}%")
        m4.metric("Чеков/Строк", len(df_full))
        
        # Топ блюд за всё время
        df_items = df_full.groupby(df_full.columns[0])[['Выручка с НДС', 'Себестоимость']].sum().reset_index()
        df_items['Фудкост'] = df_items['Себестоимость'] / df_items['Выручка с НДС'] * 100
        
        top_items = df_items.sort_values('Выручка с НДС', ascending=False).head(10)
        
        fig = px.bar(top_items, x=top_items.columns[0], y='Выручка с НДС', 
                     color='Фудкост', color_continuous_scale='RdYlGn_r', title="Топ-10 блюд за весь период")
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- РЕЖИМ: КОНКРЕТНЫЙ ДЕНЬ ----------------
    else:
        # Парсим выбранную дату обратно в объект
        current_date = datetime.strptime(selected_option, '%d.%m.%Y')
        
        # Фильтруем данные
        df_day = df_full[df_full['Дата_Отчета'] == current_date]
        
        # Считаем показатели дня
        day_rev = df_day['Выручка с НДС'].sum()
        day_cost = df_day['Себестоимость'].sum()
        day_fc = (day_cost / day_rev * 100) if day_rev > 0 else 0
        
        # Ищем предыдущий день для сравнения
        delta_msg = "нет данных"
        prev_rev = 0
        
        # Находим индекс текущей даты в отсортированном списке
        # dates_list [5 фев, 4 фев, 3 фев...]
        try:
            curr_idx = np.where(dates_list == np.datetime64(current_date))[0][0]
            if curr_idx + 1 < len(dates_list):
                prev_date = dates_list[curr_idx + 1]
                prev_df = df_full[df_full['Дата_Отчета'] == prev_date]
                prev_rev = prev_df['Выручка с НДС'].sum()
                if prev_rev > 0:
                    diff = ((day_rev - prev_rev) / prev_rev) * 100
                    delta_msg = f"{diff:+.1f}%"
        except:
            pass

        # Метрики
        st.subheader(f"Детализация за {current_date.strftime('%d %B %Y')}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Выручка", f"{day_rev:,.0f} ₽", delta_msg)
        m2.metric("Себестоимость", f"{day_cost:,.0f} ₽")
        m3.metric("Фуд-кост дня", f"{day_fc:.1f}%")

        # Табы
        tab1, tab2, tab3 = st.tabs(["📊 Меню (ABC)", "🚀 Прогноз", "📋 Данные"])
        
        with tab1:
            col_abc1, col_abc2 = st.columns([2, 1])
            with col_abc1:
                top_day = df_day.sort_values('Выручка с НДС', ascending=False).head(10)
                fig = px.bar(top_day, x=top_day.columns[0], y='Выручка с НДС',
                             color='Фудкост', color_continuous_scale='RdYlGn_r',
                             title="Топ продаж дня")
                st.plotly_chart(fig, use_container_width=True)
            with col_abc2:
                st.write("⚠️ **Высокий кост (>35%):**")
                high_cost = df_day[df_day['Фудкост'] > 35].sort_values('Фудкост', ascending=False)
                st.dataframe(high_cost[['Склады', 'Фудкост']].style.format({'Фудкост': "{:.1f}%"}), height=400)

        with tab2:
            st.info("Прогноз строится на основе динамики последних дней.")
            # График динамики + Прогноз
            daily_grp = df_full.groupby('Дата_Отчета')['Выручка с НДС'].sum().reset_index()
            
            # Простейший прогноз (среднее за 3 дня)
            last_3_avg = daily_grp['Выручка с НДС'].tail(3).mean()
            if pd.isna(last_3_avg): last_3_avg = day_rev
            
            future_days = [daily_grp['Дата_Отчета'].max() + timedelta(days=i) for i in range(1, 3)]
            future_vals = [last_3_avg * 1.02, last_3_avg * 1.05] # Пример роста выходных
            
            fig_trend = go.Figure()
            # Факт
            fig_trend.add_trace(go.Scatter(x=daily_grp['Дата_Отчета'], y=daily_grp['Выручка с НДС'],
                                           mode='lines+markers', name='Факт', line=dict(color='blue')))
            # Прогноз
            fig_trend.add_trace(go.Scatter(x=future_days, y=future_vals,
                                           mode='lines+markers', name='Прогноз', line=dict(color='green', dash='dash')))
            
            st.plotly_chart(fig_trend, use_container_width=True)

        with tab3:
            st.dataframe(df_day)

else:
    st.info("👈 Загрузите файлы слева (выберите сразу все 5 штук!)")
