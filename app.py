import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import re
from io import BytesIO
from datetime import datetime

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="RestoAnalytics AI", layout="wide")
st.title("📊 Ежедневная аналитика (История)")

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def extract_date_from_header(df_raw):
    """Пытаемся найти дату в заголовке файла (строки 0-4)"""
    # Обычно дата в строке вида "Анализ продаж за 05.02.2026"
    text_blob = " ".join(df_raw.iloc[0:5, 0].astype(str).tolist())
    match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text_blob)
    if match:
        return datetime.strptime(match.group(1), '%d.%m.%Y')
    return None

def process_single_file(file_content, filename=""):
    """Читает один файл и превращает его в таблицу данных"""
    try:
        # Читаем сначала заголовок, чтобы найти дату
        if isinstance(file_content, BytesIO):
            file_content.seek(0)
        
        # Сначала читаем "грязный" верх, чтобы найти дату
        try:
            df_raw = pd.read_excel(file_content, header=None, nrows=10)
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df_raw = pd.read_csv(file_content, header=None, nrows=10, encoding='utf-8', sep=None, engine='python')
            
        report_date = extract_date_from_header(df_raw)
        
        # Если дату не нашли внутри, пробуем из имени файла, иначе - сегодня
        if not report_date:
            report_date = datetime.now() 

        # Теперь читаем саму таблицу (header=5 по твоей структуре)
        if isinstance(file_content, BytesIO): file_content.seek(0)
        try:
            df = pd.read_excel(file_content, header=5)
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df = pd.read_csv(file_content, header=5)

        # Очистка
        df.columns = df.columns.str.strip()
        col_name = df.columns[0] # Скорее всего 'Склады' или 'Номенклатура'
        df = df.dropna(subset=[col_name])
        df = df[df[col_name] != "Итого"]
        
        # Числа
        cols_to_num = ['Количество', 'Себестоимость', 'Выручка с НДС', 'Фудкост']
        for col in cols_to_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(' ', '').str.replace(',', '.'), errors='coerce').fillna(0)
        
        # Добавляем колонку с датой этого отчета
        df['Дата_Отчета'] = report_date
        return df
        
    except Exception as e:
        # st.error(f"Ошибка чтения файла {filename}: {e}")
        return None

# --- ЗАГРУЗКА С ЯНДЕКСА (МАССОВАЯ) ---
def load_all_from_yandex(folder_path):
    token = st.secrets.get("YANDEX_TOKEN")
    if not token:
        st.error("Нет токена Яндекс.Диска!")
        return []

    headers = {'Authorization': f'OAuth {token}'}
    api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
    params = {'path': folder_path, 'limit': 100} # Берем до 100 файлов
    
    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code != 200:
        st.error(f"Ошибка доступа: {response.status_code}")
        return []
        
    items = response.json().get('_embedded', {}).get('items', [])
    
    data_frames = []
    progress_bar = st.progress(0)
    
    # Фильтруем только файлы xlsx/csv
    files = [i for i in items if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
    
    for idx, item in enumerate(files):
        download_url = item['file']
        file_resp = requests.get(download_url, headers=headers)
        file_bytes = BytesIO(file_resp.content)
        
        df = process_single_file(file_bytes, item['name'])
        if df is not None:
            data_frames.append(df)
        
        progress_bar.progress((idx + 1) / len(files))
        
    progress_bar.empty()
    return data_frames

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("Источник данных")
data_source = st.sidebar.radio("Режим:", ["Ручная загрузка (Архив)", "Яндекс.Диск (Авто)"])

all_data = []

if data_source == "Ручная загрузка (Архив)":
    # Разрешаем грузить МНОГО файлов сразу
    uploaded_files = st.sidebar.file_uploader("Выберите ВСЕ отчеты за месяц", type=['csv', 'xlsx'], accept_multiple_files=True)
    if uploaded_files:
        for file in uploaded_files:
            df = process_single_file(file, file.name)
            if df is not None:
                all_data.append(df)

elif data_source == "Яндекс.Диск (Авто)":
    yandex_folder = st.sidebar.text_input("Папка на Диске:", value="/Отчеты_Ресторан")
    if st.sidebar.button("Сканировать папку"):
        with st.spinner('Скачиваем и обрабатываем отчеты...'):
            all_data = load_all_from_yandex(yandex_folder)

# --- ОСНОВНАЯ ЛОГИКА ---
if all_data:
    # 1. Объединяем всё в одну таблицу
    df_full = pd.concat(all_data, ignore_index=True)
    df_full = df_full.sort_values(by='Дата_Отчета')
    
    # 2. Агрегируем данные по дням (Сумма выручки за каждый день)
    daily_stats = df_full.groupby('Дата_Отчета')[['Выручка с НДС', 'Себестоимость']].sum().reset_index()
    daily_stats['FoodCost_Percent'] = daily_stats['Себестоимость'] / daily_stats['Выручка с НДС'] * 100
    
    # Берем последний доступный день как "Сегодня"
    last_date = daily_stats['Дата_Отчета'].max()
    df_today = df_full[df_full['Дата_Отчета'] == last_date]
    
    # --- СВОДКА (METRICS) ---
    st.subheader(f"Сводка на {last_date.strftime('%d.%m.%Y')}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Данные за "сегодня"
    curr_rev = daily_stats[daily_stats['Дата_Отчета'] == last_date]['Выручка с НДС'].values[0]
    curr_cost = daily_stats[daily_stats['Дата_Отчета'] == last_date]['Себестоимость'].values[0]
    
    # Данные за "предыдущий загруженный день"
    if len(daily_stats) > 1:
        prev_date = daily_stats.iloc[-2]['Дата_Отчета']
        prev_rev = daily_stats.iloc[-2]['Выручка с НДС']
        delta_rev = ((curr_rev - prev_rev) / prev_rev) * 100
        delta_label = f"{delta_rev:.1f}% (к {prev_date.strftime('%d.%m')})"
    else:
        delta_label = "Нет данных"

    col1.metric("Выручка", f"{curr_rev:,.0f} ₽", delta_label)
    col2.metric("Себестоимость", f"{curr_cost:,.0f} ₽", "")
    col3.metric("Загружено дней", f"{len(daily_stats)}", "История")
    
    # --- ГРАФИКИ ---
    tab1, tab2 = st.tabs(["📈 Общая динамика", "🍔 Детальный анализ"])
    
    with tab1:
        # График Выручки (Реальный)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_stats['Дата_Отчета'], y=daily_stats['Выручка с НДС'], 
                                 mode='lines+markers', name='Выручка', line=dict(color='green', width=3)))
        fig.add_trace(go.Scatter(x=daily_stats['Дата_Отчета'], y=daily_stats['Себестоимость'], 
                                 mode='lines', name='Косты', line=dict(color='red', dash='dot')))
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("### Таблица по дням")
        st.dataframe(daily_stats.style.format({'Выручка с НДС': "{:,.0f}", 'Себестоимость': "{:,.0f}", 'FoodCost_Percent': "{:.1f}%"}))

    with tab2:
        st.write(f"### Топ позиций за {last_date.strftime('%d.%m')}")
        top_items = df_today.sort_values(by='Выручка с НДС', ascending=False).head(10)
        st.dataframe(top_items[['Склады', 'Количество', 'Выручка с НДС', 'Фудкост']].style.format({'Выручка с НДС': "{:.1f}"}))

else:
    st.info("👈 Загрузите файлы слева. Можно выбрать сразу 10-20 файлов при ручной загрузке, или указать папку Яндекс.Диска.")
