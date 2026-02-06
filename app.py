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
st.title("📊 Ежедневная аналитика и Итоги")

# --- ФУНКЦИИ ОБРАБОТКИ ---
def extract_date_from_header(df_raw):
    text_blob = " ".join(df_raw.iloc[0:5, 0].astype(str).tolist())
    match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text_blob)
    if match:
        return datetime.strptime(match.group(1), '%d.%m.%Y')
    return None

def process_single_file(file_content, filename=""):
    try:
        if isinstance(file_content, BytesIO): file_content.seek(0)
        try:
            df_raw = pd.read_excel(file_content, header=None, nrows=10)
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df_raw = pd.read_csv(file_content, header=None, nrows=10, encoding='utf-8', sep=None, engine='python')
            
        report_date = extract_date_from_header(df_raw)
        if not report_date: report_date = datetime.now() 

        if isinstance(file_content, BytesIO): file_content.seek(0)
        try:
            df = pd.read_excel(file_content, header=5)
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df = pd.read_csv(file_content, header=5)

        df.columns = df.columns.str.strip()
        col_name = df.columns[0] 
        df = df.dropna(subset=[col_name])
        df = df[df[col_name] != "Итого"]
        
        cols_to_num = ['Количество', 'Себестоимость', 'Выручка с НДС']
        for col in cols_to_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(' ', '').str.replace(',', '.'), errors='coerce').fillna(0)
        
        # Фудкост считаем сами, чтобы не зависеть от кривых процентов в файле
        df['Фудкост'] = df.apply(lambda x: (x['Себестоимость'] / x['Выручка с НДС'] * 100) if x['Выручка с НДС'] > 0 else 0, axis=1)
        
        df['Дата_Отчета'] = report_date
        return df
    except Exception as e:
        return None

def load_all_from_yandex(folder_path):
    token = st.secrets.get("YANDEX_TOKEN")
    if not token:
        st.error("Нет токена Яндекс.Диска!")
        return []
    headers = {'Authorization': f'OAuth {token}'}
    api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
    params = {'path': folder_path, 'limit': 100}
    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code != 200: return []
    items = response.json().get('_embedded', {}).get('items', [])
    data_frames = []
    files = [i for i in items if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
    if not files: return []
    
    progress_bar = st.progress(0)
    for idx, item in enumerate(files):
        file_resp = requests.get(item['file'], headers=headers)
        df = process_single_file(BytesIO(file_resp.content), item['name'])
        if df is not None: data_frames.append(df)
        progress_bar.progress((idx + 1) / len(files))
    progress_bar.empty()
    return data_frames

# --- ИНТЕРФЕЙС ---
st.sidebar.header("Источник данных")
data_source = st.sidebar.radio("Режим:", ["Ручная загрузка", "Яндекс.Диск (Авто)"])
all_data = []

if data_source == "Ручная загрузка":
    uploaded_files = st.sidebar.file_uploader("Загрузить отчеты", type=['csv', 'xlsx'], accept_multiple_files=True)
    if uploaded_files:
        for file in uploaded_files:
            df = process_single_file(file, file.name)
            if df is not None: all_data.append(df)

elif data_source == "Яндекс.Диск (Авто)":
    yandex_folder = st.sidebar.text_input("Папка:", value="/Отчеты_Ресторан")
    if st.sidebar.button("Сканировать"):
        with st.spinner('Загрузка...'):
            all_data = load_all_from_yandex(yandex_folder)

# --- ГЛАВНЫЙ БЛОК ---
if all_data:
    # 1. Сборка общей базы
    df_full = pd.concat(all_data, ignore_index=True)
    df_full = df_full.sort_values(by='Дата_Отчета')
    
    # Список доступных дат (сортируем от новых к старым)
    available_dates = sorted(df_full['Дата_Отчета'].unique(), reverse=True)
    date_options = ["📅 Весь период (ИТОГО)"] + [pd.to_datetime(d).strftime('%d.%m.%Y') for d in available_dates]
    
    # --- СЕЛЕКТОР ПЕРИОДА ---
    st.write("---")
    col_sel1, col_sel2 = st.columns([1, 3])
    selected_option = col_sel1.selectbox("Выберите период анализа:", date_options)
    
    # --- ЛОГИКА ОТОБРАЖЕНИЯ ---
    
    # 1. Если выбрано "ИТОГО"
    if "Весь период" in selected_option:
        st.subheader(f"Сводка за все загруженные дни ({len(available_dates)} дн.)")
        
        # Агрегация по всем дням
        total_rev = df_full['Выручка с НДС'].sum()
        total_cost = df_full['Себестоимость'].sum()
        avg_fc = (total_cost / total_rev * 100) if total_rev > 0 else 0
        
        # Группировка блюд за весь период (суммируем продажи одного блюда за все дни)
        group_col = df_full.columns[0] # Название блюда
        df_display = df_full.groupby(group_col)[['Количество', 'Себестоимость', 'Выручка с НДС']].sum().reset_index()
        # Пересчитываем фудкост для итогов
        df_display['Фудкост'] = df_display.apply(lambda x: (x['Себестоимость']/x['Выручка с НДС']*100) if x['Выручка с НДС']>0 else 0, axis=1)
        
        # Метрики
        m1, m2, m3 = st.columns(3)
        m1.metric("Общая Выручка", f"{total_rev:,.0f} ₽")
        m2.metric("Общий Food Cost", f"{total_cost:,.0f} ₽", f"{avg_fc:.1f}% (Avg)")
        m3.metric("Всего продано позиций", f"{df_display['Количество'].sum():,.0f}")

    # 2. Если выбрана КОНКРЕТНАЯ ДАТА
    else:
        selected_date_obj = datetime.strptime(selected_option, '%d.%m.%Y')
        st.subheader(f"Детализация за {selected_option}")
        
        # Фильтруем данные
        df_display = df_full[df_full['Дата_Отчета'] == selected_date_obj].copy()
        
        # Считаем показатели дня
        day_rev = df_display['Выручка с НДС'].sum()
        day_cost = df_display['Себестоимость'].sum()
        day_fc = (day_cost / day_rev * 100) if day_rev > 0 else 0
        
        # Пытаемся сравнить с предыдущим днем
        current_idx = available_dates.index(np.datetime64(selected_date_obj))
        delta_label = "Нет данных"
        if current_idx + 1 < len(available_dates): # Есть день раньше
            prev_date = available_dates[current_idx + 1]
            prev_df = df_full[df_full['Дата_Отчета'] == prev_date]
            prev_rev = prev_df['Выручка с НДС'].sum()
            if prev_rev > 0:
                delta = ((day_rev - prev_rev) / prev_rev) * 100
                delta_label = f"{delta:+.1f}% к {pd.to_datetime(prev_date).strftime('%d.%m')}"

        # Метрики
        m1, m2, m3 = st.columns(3)
        m1.metric("Выручка за день", f"{day_rev:,.0f} ₽", delta_label)
        m2.metric("Food Cost дня", f"{day_cost:,.0f} ₽", f"{day_fc:.1f}%")
        m3.metric("Чеков/Позиций", f"{df_display['Количество'].sum():,.0f}")

    # --- ГРАФИКИ (ВСЕГДА ВИДНЫ) ---
    st.write("---")
    tab1, tab2 = st.tabs(["📊 Анализ меню (ABC)", "📈 Динамика выручки"])
    
    with tab1:
        st.write(f"**Топ блюд ({selected_option})**")
        # Сортировка и топ
        top_items = df_display.sort_values(by='Выручка с НДС', ascending=False).head(15)
        
        # График
        fig_bar = px.bar(top_items, x=top_items.columns[0], y='Выручка с НДС', 
                         color='Фудкост', color_continuous_scale='RdYlGn_r',
                         text_auto='.2s', title="Топ продаж и Фудкост")
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Таблица опасных позиций
        if st.checkbox("Показать позиции с высоким фудкостом (>35%)"):
            bad_items = df_display[df_display['Фудкост'] > 35].sort_values(by='Фудкост', ascending=False)
            st.dataframe(bad_items.style.format({'Себестоимость': "{:.1f}", 'Выручка с НДС': "{:.1f}", 'Фудкост': "{:.1f}"}), use_container_width=True)

    with tab2:
        # График динамики строим по ВСЕМ загруженным данным, независимо от выбора дня
        daily_stats = df_full.groupby('Дата_Отчета')[['Выручка с НДС', 'Себестоимость']].sum().reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_stats['Дата_Отчета'], y=daily_stats['Выручка с НДС'], 
                                 mode='lines+markers', name='Выручка', line=dict(color='#00CC96', width=3)))
        fig.add_trace(go.Scatter(x=daily_stats['Дата_Отчета'], y=daily_stats['Себестоимость'], 
                                 mode='lines', name='Косты', line=dict(color='#EF553B', dash='dot')))
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👈 Загрузите данные в меню слева, чтобы увидеть аналитику.")
