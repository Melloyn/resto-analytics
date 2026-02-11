import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import numpy as np
import os
import telegram_utils
import data_engine
from io import BytesIO
from datetime import datetime, timedelta

# --- CHART THEME ---
def update_chart_layout(fig):
    fig.update_layout(
        template="plotly_dark",
        font=dict(family="Inter, sans-serif", size=13, color="#E0E0E0"),
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)", # Slight highlight
        hovermode="x unified",
        xaxis=dict(
            showgrid=False, 
            zeroline=False, 
            showline=True, 
            linecolor="rgba(255,255,255,0.2)"
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor="rgba(255,255,255,0.08)", 
            zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig

# --- V2.1 Helper ---
def get_secret(key):
    try:
        return st.secrets.get(key)
    except FileNotFoundError:
        return None

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="RestoAnalytics: Место", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Аналитика: Бар МЕСТО")

# --- CSS STYLING ---
def setup_style():
    st.markdown("""
    <style>
        /* Import Inter Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #0e1117; /* Dark background base */
        }

        /* --- GLASSMORPHISM SIDEBAR --- */
        [data-testid="stSidebar"] {
            background-color: rgba(17, 17, 17, 0.7) !important;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        }

        /* --- GLASS METRIC CARDS --- */
        [data-testid="stMetric"] {
            background: rgba(45, 45, 45, 0.4) !important; /* Lighter tint */
            backdrop-filter: blur(18px); /* Deeper blur */
            -webkit-backdrop-filter: blur(18px);
            padding: 15px !important;
            border-radius: 16px !important; /* More iOS-like */
            border: 1px solid rgba(255, 255, 255, 0.15) !important; /* Stronger border */
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important; /* Deeper shadow */
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        [data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5) !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
            background: rgba(60, 60, 60, 0.5) !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.6);
        }

        [data-testid="stMetricValue"] {
            font-size: 26px;
            font-weight: 600;
            color: #FFF;
        }
        
        [data-testid="stMetricDelta"] {
            font-size: 14px;
        }

        /* --- HEADERS & TEXT --- */
        h1, h2, h3 {
            font-weight: 600;
            letter-spacing: -0.5px;
            color: #FFF;
        }
        
        /* --- EXPANDER STYLING (GLASS) --- */
        .streamlit-expanderHeader {
            background-color: rgba(30, 30, 30, 0.5);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        /* --- BUTTONS (Optional Polish) --- */
        button[kind="primary"] {
            background: linear-gradient(135deg, #FF4B4B 0%, #FF2B2B 100%);
            border: none;
            box-shadow: 0 4px 12px rgba(255, 75, 75, 0.3);
            transition: all 0.3s ease;
        }
        button[kind="primary"]:hover {
            box-shadow: 0 6px 16px rgba(255, 75, 75, 0.5);
            transform: translateY(-2px);
        }

        /* --- SIDEBAR ELEMENTS --- */
        .stSelectbox label, .stRadio label {
            font-weight: 600 !important;
            color: rgba(255,255,255,0.9) !important;
        }

        /* --- TABLE STYLING --- */
        [data-testid="stDataFrame"] {
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            overflow: hidden;
        }
        
        /* --- STREAMLIT HEADER --- */
        header[data-testid="stHeader"] {
            background: transparent !important;
            backdrop-filter: blur(5px);
        }

        /* Remove Deploy Button & Padding */
        #MainMenu {visibility: hidden;}
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
    </style>
    """, unsafe_allow_html=True)

setup_style()

# --- ИНИЦИАЛИЗАЦИЯ ПАМЯТИ ---
if 'df_full' not in st.session_state:
    st.session_state.df_full = None
if 'dropped_stats' not in st.session_state:
    st.session_state.dropped_stats = {'count': 0, 'cost': 0.0, 'items': []}

# --- 1. ГРУППИРОВКА ДЛЯ МАКРО-УРОВНЯ ---



# --- SMART INSIGHTS ENGINE ---
def generate_insights(df_curr, df_prev, cur_rev, prev_rev, cur_fc):
    with st.expander("💡 Smart Insights (Анализ Аномалий)", expanded=True):
        insights = data_engine.calculate_insights(df_curr, df_prev, cur_rev, prev_rev, cur_fc)
        
        level_map = {
            'error': st.error,
            'warning': st.warning,
            'info': st.info,
            'success': st.success
        }
        
        for note in insights:
            # Render using the appropriate Streamlit function
            # Some messages in data_engine have bold markdown, st handles that fine.
            if note['level'] in level_map:
                level_map[note['level']](note['message'])

@st.cache_data(ttl=3600, show_spinner="Скачиваем данные с Яндекс.Диска...")
def load_all_from_yandex(root_path):
    token = get_secret("YANDEX_TOKEN")
    if not token: return [], {'count': 0, 'cost': 0.0, 'items': []}
    
    headers = {'Authorization': f'OAuth {token}'}
    api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
    
    all_dfs = []
    # Master accumulator for dropped stats (pure, no session_state)
    master_dropped = {'count': 0, 'cost': 0.0, 'items': []}
    
    def list_items(path, limit=1000):
        items_acc = []
        offset = 0

        while True:
            params = {'path': path, 'limit': limit, 'offset': offset}
            resp = requests.get(api_url, headers=headers, params=params, timeout=20)
            if resp.status_code != 200:
                st.warning(f"⚠️ Ошибка чтения папки '{path}' (status {resp.status_code})")
                return items_acc

            page_items = resp.json().get('_embedded', {}).get('items', [])
            if not page_items:
                break

            items_acc.extend(page_items)
            if len(page_items) < limit:
                break
            offset += limit

        return items_acc

    # Helper: Pure function returning (processed_dfs, batch_dropped_stats)
    def process_items(files, venue_tag):
        processed = []
        batch_dropped = {'count': 0, 'cost': 0.0, 'items': []}
        
        for item in files:
            try:
                file_resp = requests.get(item['file'], headers=headers, timeout=20)
                if file_resp.status_code != 200:
                    st.warning(f"⚠️ Не удалось скачать {item['name']} (Status {file_resp.status_code})")
                    continue
                    
                df, error, warnings, dropped = data_engine.process_single_file(BytesIO(file_resp.content), filename=item['name'])
                
                # Accumulate dropped stats for this batch
                if dropped:
                    batch_dropped['count'] += dropped['count']
                    batch_dropped['cost'] += dropped['cost']
                    batch_dropped['items'].extend(dropped['items'])

                if error:
                    st.warning(f"{item['name']}: {error}")
                for warn in warnings:
                    st.info(f"{item['name']}: {warn}")
                if df is not None:
                    df['Venue'] = venue_tag
                    processed.append(df)
            except Exception as e:
                st.warning(f"⚠️ Ошибка обработки {item['name']}: {e}")
                continue
        
        return processed, batch_dropped

    # Helper to merge stats
    def merge_stats(source):
        master_dropped['count'] += source['count']
        master_dropped['cost'] += source['cost']
        master_dropped['items'].extend(source['items'])

    try:
        # 1. Get Root Items (with pagination)
        items = list_items(root_path, limit=1000)
        if not items:
            return [], master_dropped
        
        folders = [i for i in items if i['type'] == 'dir']
        root_files = [i for i in items if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
        
        # 2. Process Root Files -> Venue = 'Mesto'
        if root_files:
             dfs, d_stats = process_items(root_files, 'Mesto')
             all_dfs.extend(dfs)
             merge_stats(d_stats)

        # 3. Recursive Process Subfolders
        def get_files_recursive(path):
            all_files_in_path = []
            try:
                itms = list_items(path, limit=1000)

                # Files in this dir
                files = [i for i in itms if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
                all_files_in_path.extend(files)

                # Subdirs to recurse
                dirs = [i for i in itms if i['type'] == 'dir']
                for d in dirs:
                    all_files_in_path.extend(get_files_recursive(d['path']))
            except Exception as e:
                st.warning(f"⚠️ Ошибка обхода папки {path}: {e}")
            return all_files_in_path

        for folder in folders:
            venue_name = folder['name']
            # Get all files recursively
            venue_files = get_files_recursive(folder['path'])
            
            if venue_files:
                dfs, d_stats = process_items(venue_files, venue_name)
                all_dfs.extend(dfs)
                merge_stats(d_stats)
        
        return all_dfs, master_dropped
    except Exception as e:
        st.error(f"Error loading from Yandex: {e}")
        return [], {'count': 0, 'cost': 0.0, 'items': []}

def load_from_local_folder(root_path):
    all_dfs = []
    
    # helper to process a list of files
    def process_local_files(files, venue_tag):
        processed = []
        dropped_total = {'count': 0, 'cost': 0.0, 'items': []}
        
        for file_path in files:
            try:
                # Read file content
                with open(file_path, 'rb') as f:
                    content = BytesIO(f.read())
                
                filename = os.path.basename(file_path)
                df, error, warnings, dropped = data_engine.process_single_file(content, filename=filename)
                
                # Accumulate
                if dropped:
                    dropped_total['count'] += dropped['count']
                    dropped_total['cost'] += dropped['cost']
                    dropped_total['items'].extend(dropped['items'])

                if error:
                    st.warning(f"{filename}: {error}")
                for warn in warnings:
                    st.info(f"{filename}: {warn}")
                if df is not None:
                    df['Venue'] = venue_tag
                    processed.append(df)
            except Exception as e:
                st.warning(f"Error reading {file_path}: {e}")
        
        return processed, dropped_total

    try:
        if not os.path.exists(root_path):
            st.error(f"Папка не найдена: {root_path}")
            return [], {'count': 0, 'cost': 0.0, 'items': []}

        dropped_total = {'count': 0, 'cost': 0.0, 'items': []}

        # 1. Walk through directory
        for root, dirs, files in os.walk(root_path):
            # Determine Venue from folder name relative to root_path
            rel_path = os.path.relpath(root, root_path)
            
            if rel_path == ".":
                venue_name = "Mesto" # Default for root
            else:
                # Use the first level folder as Venue Name
                # e.g. root/barmesto/2026 -> venue = barmesto
                parts = rel_path.split(os.sep)
                venue_name = parts[0]
            
            # Filter for Excel/CSV
            target_files = [os.path.join(root, f) for f in files if f.endswith(('.xlsx', '.csv')) and not f.startswith('~$')]
            
            if target_files:
                st.write(f"📂 Scanning {venue_name} ({len(target_files)} files)...")
                dfs, dropped_sub = process_local_files(target_files, venue_name)
                all_dfs.extend(dfs)
                # Accumulate
                dropped_total['count'] += dropped_sub['count']
                dropped_total['cost'] += dropped_sub['cost']
                dropped_total['items'].extend(dropped_sub['items'])

        return all_dfs, dropped_total
    except Exception as e:
        st.error(f"Error loading local files: {e}")
        return [], {'count': 0, 'cost': 0.0, 'items': []}

# --- AUTO-LOAD CACHE ON STARTUP ---
CACHE_FILE = "data_cache.parquet"
if st.session_state.df_full is None and os.path.exists(CACHE_FILE):
    try:
        st.session_state.df_full = pd.read_parquet(CACHE_FILE)
        # Optional: st.toast("Данные восстановлены из кеша", icon="💾")
    except Exception:
        pass # Fail silently, user can load manually

# --- 1. SIDEBAR: DATA LOADING ---
# --- 1. SIDEBAR: DATA LOADING ---
with st.sidebar:
    st.title("🎛 Меню")
    
    # --- DATA SOURCE (EXPANDER) ---
    with st.expander("📂 Источник данных", expanded=False):
        source_mode = st.radio("Режим:", ["Яндекс.Диск", "Локальная папка", "Ручная загрузка"], label_visibility="collapsed")

        # --- YANDEX DISK ---
        if source_mode == "Яндекс.Диск":
            yandex_path = st.text_input("Папка на Диске:", "RestoAnalytic")
            if st.button("🚀 Скачать отчеты", type="primary", use_container_width=True):
                if not get_secret("YANDEX_TOKEN"):
                     st.error("⚠️ Нет токена!")
                else:
                    temp_data, dropped_load = load_all_from_yandex(yandex_path)
                    if temp_data:
                        st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')
                        
                        # Update Stats
                        if dropped_load:
                            st.session_state.dropped_stats = dropped_load
                            
                        st.success(f"Загружено {len(temp_data)} отчетов!")
                        st.rerun()
                    else:
                        st.warning("Файлов не найдено.")

        # --- LOCAL FOLDER ---
        elif source_mode == "Локальная папка":
            local_path = st.text_input("Путь к папке:", ".")
            if st.button(" Сканировать папку", type="primary", use_container_width=True):
                temp_data, dropped_load = load_from_local_folder(local_path)
                if temp_data:
                    st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')
                    
                    # Update Stats
                    if dropped_load:
                        st.session_state.dropped_stats = dropped_load
                        
                    st.success(f"Загружено {len(temp_data)} отчетов!")
                    st.rerun()
                else:
                    st.warning("Файлов не найдено.")

        # --- MANUAL UPLOAD ---
        elif source_mode == "Ручная загрузка":
            uploaded_files = st.file_uploader("Загрузить (CSV/Excel)", accept_multiple_files=True)
            if uploaded_files and st.button("📥 Обработать файлы", type="primary", use_container_width=True):
                temp_data = []
                st.session_state.dropped_stats = {'count': 0, 'cost': 0.0, 'items': []}
                
                for f in uploaded_files:
                    df_res = data_engine.process_single_file(f, f.name)
                    # Unwrap 4 args
                    if isinstance(df_res, tuple) and len(df_res) == 4:
                        df, error, warnings, dropped = df_res
                    else:
                        df, error, warnings, dropped = None, "Unknown error", [], None
                    
                    # Accumulate dropped
                    if dropped:
                        st.session_state.dropped_stats['count'] += dropped['count']
                        st.session_state.dropped_stats['cost'] += dropped['cost']
                        st.session_state.dropped_stats['items'].extend(dropped['items'])

                    if error: st.warning(error)
                    for w in warnings: st.warning(w)
                    if df is not None: temp_data.append(df)
                
                if temp_data:
                    st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')
                    st.success("Файлы обработаны!")
                    st.rerun()

    # --- ADVANCED OPTIONS (Cache, Reset) ---
    with st.expander("⚙️ Технические опции"):
        CACHE_FILE = "data_cache.parquet"
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Кеш", use_container_width=True):
                if st.session_state.df_full is not None:
                    st.session_state.df_full.to_parquet(CACHE_FILE, index=False)
                    st.success("ОК!")
                else:
                    st.warning("Пусто")
        with col2:
            if st.button("🚀 Load", use_container_width=True):
                if os.path.exists(CACHE_FILE):
                     st.session_state.df_full = pd.read_parquet(CACHE_FILE)
                     st.success("ОК!")
                     st.rerun()
                else:
                     st.warning("Нет")
        
        if st.button("🗑 Сброс", use_container_width=True):
            st.cache_data.clear()
            st.session_state.df_full = None
            st.session_state.dropped_stats = {'count': 0, 'cost': 0.0, 'items': []}
            st.rerun()
            
    # --- DEBUG INFO IN SIDEBAR ---
    with st.expander("🐞 Debug: Отброшенные", expanded=False):
        if st.session_state.dropped_stats and st.session_state.dropped_stats['count'] > 0:
            st.write(f"**Кол-во:** {st.session_state.dropped_stats['count']}")
            st.write(f"**Cумма:** {st.session_state.dropped_stats['cost']:,.0f} ₽")
            
            # Show top items
            items_df = pd.DataFrame(st.session_state.dropped_stats['items'])
            if not items_df.empty:
                items_df = items_df.sort_values(by='Себестоимость', ascending=False).head(20)
                st.dataframe(items_df, hide_index=True)


# --- CUSTOM CATEGORY LOGIC (GLOBAL) ---
MAPPING_FILE = "category_mapping.json"

def load_custom_categories():
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_custom_categories(new_map):
    current_map = load_custom_categories()
    current_map.update(new_map)
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(current_map, f, ensure_ascii=False, indent=4)

# Load and Apply Custom Categories globally to df_full
if st.session_state.df_full is not None:
    custom_cats = load_custom_categories()
    if custom_cats:
        st.session_state.df_full['Категория'] = st.session_state.df_full.apply(
            lambda x: custom_cats.get(x['Блюдо'], x['Категория']), axis=1
        )
        
        # --- GLOBAL FILTER: DELETE IGNORED ITEMS ---
        # Remove rows where category is "⛔ Исключить из отчетов"
        st.session_state.df_full = st.session_state.df_full[st.session_state.df_full['Категория'] != "⛔ Исключить из отчетов"]

# --- ОСНОВНАЯ ЛОГИКА ---
tg_token = get_secret("TELEGRAM_TOKEN")
tg_chat = get_secret("TELEGRAM_CHAT_ID")

if st.session_state.df_full is not None:

    # --- SIDEBAR: FILTERS (EXPANDER) ---
    with st.sidebar.expander("� Фильтры периода", expanded=False):

        # 1. VENUE SELECTOR
        selected_venue = "Все заведения"
        if 'Venue' in st.session_state.df_full.columns:
            unique_venues = sorted(st.session_state.df_full['Venue'].astype(str).unique())
            if len(unique_venues) > 1 or (len(unique_venues) == 1 and unique_venues[0] != 'nan'):
                 selected_venue = st.selectbox("🏠 Заведение:", ["Все заведения"] + unique_venues)

        # ЛЕЧЕНИЕ ДАННЫХ В ПАМЯТИ (Если вдруг нет колонки)
        if 'Поставщик' not in st.session_state.df_full.columns:
            st.session_state.df_full['Поставщик'] = 'Не указан'

        # ФИЛЬТРАЦИЯ
        if selected_venue != "Все заведения":
            df_full = st.session_state.df_full[st.session_state.df_full['Venue'] == selected_venue].copy()
        else:
            df_full = st.session_state.df_full.copy()
        
        # MACRO
        df_full['Макро_Категория'] = df_full['Категория'].apply(data_engine.get_macro_category)

        dates_list = sorted(df_full['Дата_Отчета'].unique(), reverse=True)

        # 2. PERIOD SELECTOR
        # Выбор режима: Месяц (для KPI/MoM) или Произвольный (для детального анализа)
        period_mode = st.radio("Режим:", ["📅 Месяц (Сравнение)", "📆 Интервал дат"], label_visibility="collapsed", horizontal=True)
        
        df_current = pd.DataFrame()
        df_prev = pd.DataFrame()
        prev_label = ""
        target_date = datetime.now()
        
        if period_mode == "📅 Месяц (Сравнение)":
            df_full['Month_Year'] = df_full['Дата_Отчета'].dt.to_period('M')
            available_months = sorted(df_full['Month_Year'].unique(), reverse=True)
            
            if available_months:
                selected_month = st.selectbox("Выбери месяц:", available_months, format_func=lambda x: x.strftime('%B %Y'))
                compare_options = ["Предыдущий месяц", "Тот же месяц (год назад)", "Нет"]
                compare_mode = st.selectbox("Сравнить с:", compare_options)
                
                # Текущий
                df_current = df_full[df_full['Month_Year'] == selected_month]
                target_date = df_current['Дата_Отчета'].max()
                
                # Сравнение
                if compare_mode == "Предыдущий месяц":
                    prev_month = selected_month - 1
                    df_prev = df_full[df_full['Month_Year'] == prev_month]
                    prev_label = prev_month.strftime('%B %Y')
                elif compare_mode == "Тот же месяц (год назад)":
                    prev_month = selected_month - 12
                    df_prev = df_full[df_full['Month_Year'] == prev_month]
                    prev_label = prev_month.strftime('%B %Y')
        else:
            # Режим ИНТЕРВАЛ
            min_date = df_full['Дата_Отчета'].min().date()
            max_date = df_full['Дата_Отчета'].max().date()
            date_range = st.date_input("Выберите даты:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
            
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_d, end_d = date_range
                df_current = df_full[(df_full['Дата_Отчета'].dt.date >= start_d) & (df_full['Дата_Отчета'].dt.date <= end_d)]
                target_date = end_d
                
                # --- COMPARISON LOGIC ---
                compare_options = ["Нет", "Предыдущий период", "Тот же период (год назад)"]
                compare_mode = st.selectbox("Сравнить с:", compare_options)
                
                if compare_mode == "Предыдущий период":
                    delta = end_d - start_d
                    prev_end = start_d - timedelta(days=1)
                    prev_start = prev_end - delta
                    prev_label = f"{prev_start.strftime('%d.%m')} - {prev_end.strftime('%d.%m')}"
                    
                    df_prev = df_full[(df_full['Дата_Отчета'].dt.date >= prev_start) & (df_full['Дата_Отчета'].dt.date <= prev_end)]
                    
                elif compare_mode == "Тот же период (год назад)":
                    # Simple Shift - 1 Year
                    def safe_year_sub(d):
                        try: return d.replace(year=d.year - 1)
                        except ValueError: return d.replace(year=d.year - 1, day=28)
                    
                    prev_start = safe_year_sub(start_d)
                    prev_end = safe_year_sub(end_d)
                    prev_label = f"{prev_start.strftime('%d.%m.%y')} - {prev_end.strftime('%d.%m.%y')}"
                    
                    df_prev = df_full[(df_full['Дата_Отчета'].dt.date >= prev_start) & (df_full['Дата_Отчета'].dt.date <= prev_end)]
                else:
                    prev_label = "Без сравнения"
                    df_prev = pd.DataFrame()
    
            else:
                st.warning("Выберите корректный интервал")

    # --- SIDEBAR: ACTIONS & EXPORT (EXPANDER) ---
    with st.sidebar.expander("⚡ Действия и Экспорт", expanded=False):
        
        if st.button("📤 Отчет в Telegram", use_container_width=True):
            if not tg_token or not tg_chat:
                st.error("❌ Нет токена/чата!")
            elif st.session_state.df_full is None:
                st.warning("⚠️ Нет данных.")
            else:
                with st.spinner("Формирую отчет..."):
                    report_text = telegram_utils.format_report(st.session_state.df_full, target_date)
                    success, msg = telegram_utils.send_to_all(tg_token, tg_chat, report_text)
                    if success: st.success("Отправлено!")
                    else: st.error(msg)
        
        st.divider()
        
        if not df_current.empty:
            # --- EXPORT SETTINGS ---
            sort_opt = st.radio(
                "Сортировка:",
                ["💰 По Выручке", "📉 По Фуд-косту", "📦 По Количеству"],
                index=0
            )
            
            # Function to convert DF to Excel with fallback AND CHARTS
            @st.cache_data
            def convert_df(df, sort_mode):
                output = BytesIO()
                try:
                    # 1. Prepare Data
                    exp_df = df.copy()
                    
                    # Normalize 'Cost' column name (handle 'Фудкост' if present)
                    if 'Фудкост' in exp_df.columns and 'Кост %' not in exp_df.columns:
                        exp_df['Кост %'] = exp_df['Фудкост']
                    
                    # Calculate Cost % if still missing
                    if 'Кост %' not in exp_df.columns:
                         exp_df['Кост %'] = (exp_df['Себестоимость'] / exp_df['Выручка с НДС'] * 100).fillna(0)
                    
                    # 2. Sort
                    if "Выручке" in sort_mode:
                        exp_df = exp_df.sort_values(by='Выручка с НДС', ascending=False)
                        sort_col = 'Выручка'
                    elif "Фуд-косту" in sort_mode:
                        exp_df = exp_df.sort_values(by='Кост %', ascending=False)
                        sort_col = 'Кост %'
                    elif "Количеству" in sort_mode:
                        exp_df = exp_df.sort_values(by='Количество', ascending=False)
                        sort_col = 'Кол-во'
                    else:
                        sort_col = 'Выручка'
                    
                    # 3. Filter & Rename Columns
                    cols_map = {
                        'Блюдо': 'Наименование', 
                        'Количество': 'Кол-во', 
                        'Себестоимость': 'Себест.', 
                        'Выручка с НДС': 'Выручка', 
                        'Кост %': 'Кост %', 
                        'Категория': 'Категория'
                    }
                    
                    # Select only existing columns from the map
                    available_cols = [c for c in cols_map.keys() if c in exp_df.columns]
                    final_df = exp_df[available_cols].rename(columns=cols_map)
                    
                    # 4. Write to Excel using XlsxWriter
                    try:
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            final_df.to_excel(writer, index=False, sheet_name='Report')
                            workbook  = writer.book
                            worksheet = writer.sheets['Report']

                            # --- FORMATTING ---
                            # Formats
                            fmt_header = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                            fmt_money = workbook.add_format({'num_format': '#,##0 ₽'})
                            fmt_pct = workbook.add_format({'num_format': '0.0%"'}) # Quote to avoid excel issues
                            fmt_int = workbook.add_format({'num_format': '0'})

                            # Apply Header Format
                            for col_num, value in enumerate(final_df.columns.values):
                                worksheet.write(0, col_num, value, fmt_header)
                                
                            # Apply Column Widths & Formats
                            for i, col in enumerate(final_df.columns):
                                width = 15
                                fmt = None
                                if col in ['Выручка', 'Себест.']:
                                    width = 18
                                    fmt = fmt_money
                                elif col == 'Кост %':
                                    width = 12
                                    fmt = fmt_pct
                                elif col == 'Кол-во':
                                    width = 10
                                    fmt = fmt_int
                                elif col == 'Наименование':
                                    width = 40
                                
                                worksheet.set_column(i, i, width, fmt)

                            # --- CHARTS ---
                            charts_sheet = workbook.add_worksheet('Charts')
                            
                            # 1. COLUMN CHART (Top 10 Items)
                            chart_col = workbook.add_chart({'type': 'column'})
                            max_row = min(10, len(final_df))
                            try:
                                val_idx = final_df.columns.get_loc(sort_col)
                                chart_col.add_series({
                                    'name':       [ 'Report', 0, val_idx],
                                    'categories': [ 'Report', 1, 0, max_row, 0], # Top 10 names
                                    'values':     [ 'Report', 1, val_idx, max_row, val_idx], # Top 10 values
                                    'data_labels': {'value': True},
                                    'gap':        30,
                                })
                                chart_col.set_title ({'name': f'Топ-10: {sort_col}'})
                                chart_col.set_x_axis({'name': 'Позиция', 'major_gridlines': {'visible': False}})
                                chart_col.set_y_axis({'name': sort_col, 'major_gridlines': {'visible': True, 'line': {'style': 'dash'}}})
                                chart_col.set_legend({'position': 'none'})
                                chart_col.set_style(11)
                                charts_sheet.insert_chart('B2', chart_col, {'x_scale': 2.5, 'y_scale': 2})
                            except:
                                pass

                            # 2. PIE CHART (Category Distribution - Micro)
                            # We need to aggregate data for the pie chart
                            if 'Категория' in final_df.columns:
                                try:
                                    # Group by Category and Sum Sort Column (e.g. Revenue)
                                    cat_df = final_df.groupby('Категория')[sort_col].sum().reset_index().sort_values(by=sort_col, ascending=False)
                                    
                                    # Write summarized data to Charts sheet (hidden/side)
                                    # Start writing at row 20 (below chart) or side
                                    # Let's write it to columns O and P on Charts sheet
                                    charts_sheet.write(0, 14, 'Категория', fmt_header)
                                    charts_sheet.write(0, 15, sort_col, fmt_header)
                                    
                                    for r_idx, row in cat_df.iterrows():
                                        charts_sheet.write(r_idx + 1, 14, row['Категория'])
                                        charts_sheet.write(r_idx + 1, 15, row[sort_col], fmt_money)
                                        
                                    # Create Pie Chart
                                    chart_pie = workbook.add_chart({'type': 'pie'})
                                    cat_len = len(cat_df)
                                    
                                    chart_pie.add_series({
                                        'name':       f'Доли (Микро-Категории)',
                                        'categories': [ 'Charts', 1, 14, cat_len, 14],
                                        'values':     [ 'Charts', 1, 15, cat_len, 15],
                                        'data_labels': {'percentage': True},
                                    })
                                    
                                    chart_pie.set_title({'name': f'Доли (Микро): {sort_col}'})
                                    chart_pie.set_style(10)
                                    
                                    # Insert Pie Chart next to Column Chart
                                    charts_sheet.insert_chart('J2', chart_pie, {'x_scale': 1.5, 'y_scale': 1.5})
                                except Exception as e_pie:
                                    pass

                            # 3. DONUT CHART (Macro-Category Distribution)
                            if 'Макро_Категория' in exp_df.columns: # Check original DF for Macro
                                try:
                                    # Aggregate
                                    macro_df = exp_df.groupby('Макро_Категория')[sort_col].sum().reset_index().sort_values(by=sort_col, ascending=False)
                                    
                                    # Write Data
                                    charts_sheet.write(0, 17, 'Макро-Группа', fmt_header) # Col R
                                    charts_sheet.write(0, 18, sort_col, fmt_header)       # Col S
                                    
                                    for r_idx, row in macro_df.iterrows():
                                        charts_sheet.write(r_idx + 1, 17, row['Макро_Категория'])
                                        charts_sheet.write(r_idx + 1, 18, row[sort_col], fmt_money)
                                        
                                    # Create Donut Chart
                                    chart_donut = workbook.add_chart({'type': 'doughnut'})
                                    macro_len = len(macro_df)
                                    
                                    chart_donut.add_series({
                                        'name':       f'Структура (Макро)',
                                        'categories': [ 'Charts', 1, 17, macro_len, 17],
                                        'values':     [ 'Charts', 1, 18, macro_len, 18],
                                        'data_labels': {'percentage': True},
                                    })
                                    
                                    chart_donut.set_title({'name': f'Структура Выручки (Макро)'})
                                    chart_donut.set_style(10)
                                    chart_donut.set_rotation(90)
                                    
                                    # Insert Donut Chart below Column Chart
                                    charts_sheet.insert_chart('B18', chart_donut, {'x_scale': 1.5, 'y_scale': 1.5})

                                except Exception as e_donut:
                                    pass # Fail silently


                    except Exception as e_xlsx:
                        # FALLBACK if xlsxwriter fails (module missing? engine error?)
                        # Use openpyxl but export FINAL_DF (filtered/sorted)
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                             final_df.to_excel(writer, index=False, sheet_name='Report')

                except Exception as e:
                    # General error (conversion failed)
                    st.sidebar.error(f"Ошибка экспорта: {e}")
                    return None
                return output.getvalue()

            excel_data = convert_df(df_current, sort_opt)
            
            if excel_data:
                st.sidebar.download_button(
                    label="📊 Скачать Excel (+Графики)",
                    data=excel_data,
                    file_name=f"report_{target_date.strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.info("Нет данных для экспорта.")

    # --- KPI DISPLAY ---
    if not df_current.empty:
        # Расчет KPI
        def calc_kpis(df):
            if df.empty: return 0, 0, 0, 0
            rev = df['Выручка с НДС'].sum()
            cost = df['Себестоимость'].sum()
            margin = rev - cost
            fc = (cost / rev * 100) if rev > 0 else 0
            return rev, cost, margin, fc

        cur_rev, cur_cost, cur_margin, cur_fc = calc_kpis(df_current)
        prev_rev, prev_cost, prev_margin, prev_fc = calc_kpis(df_prev)
        
        # Дельты
        delta_rev = cur_rev - prev_rev if not df_prev.empty else 0
        delta_margin = cur_margin - prev_margin if not df_prev.empty else 0
        delta_fc = cur_fc - prev_fc if not df_prev.empty else 0
        
        sub_title = "Произвольный период" if period_mode == "📆 Интервал дат" else f"{selected_month.strftime('%B %Y')} vs {prev_label if not df_prev.empty else 'Нет данных'}"
        
        # --- SMART INSIGHTS ---
        generate_insights(df_current, df_prev, cur_rev, prev_rev, cur_fc)
        
        st.write(f"### 📊 Сводка: {sub_title}")
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("💰 Выручка", f"{cur_rev:,.0f} ₽", f"{delta_rev:+,.0f} ₽" if not df_prev.empty else None)
        kpi2.metric("📉 Фуд-кост", f"{cur_fc:.1f} %", f"{delta_fc:+.1f} %" if not df_prev.empty else None, delta_color="inverse")
        kpi3.metric("💳 Маржа", f"{cur_margin:,.0f} ₽", f"{delta_margin:+,.0f} ₽" if not df_prev.empty else None)
        kpi4.metric("🧾 Позиций", len(df_current))

        # --- ГРАФИК ДИНАМИКИ ПО ДНЯМ ---
        if period_mode == "📅 Месяц (Сравнение)" and not df_current.empty:
            with st.expander("📈 Динамика Выручки (День за днём)", expanded=False):
                # Подготовка данных
                df_chart_cur = df_current.groupby(df_current['Дата_Отчета'].dt.day)['Выручка с НДС'].sum().cumsum()
                
                chart_data = pd.DataFrame({'Текущий': df_chart_cur})
                
                if not df_prev.empty and compare_mode != "Нет":
                    df_chart_prev = df_prev.groupby(df_prev['Дата_Отчета'].dt.day)['Выручка с НДС'].sum().cumsum()
                    chart_data['Прошлый'] = df_chart_prev
                
                st.line_chart(chart_data)

        df_view = df_current # Для совместимости с остальным кодом
    else:
        st.warning("Нет данных с датами.")
        df_view = df_full
        target_date = datetime.now()

    # --- НАВИГАЦИЯ ---
    tab_options = ["🔥 Инфляция", "📉 Динамика и Поставщики", "🍰 Меню и Косты", "⭐ Матрица (ABC)", "🗓 Дни недели", "📦 План Закупок", "🔮 Симулятор"]
    
    # Используем session_state для сохранения выбора вкладки, если нужно, но st.radio и так сохраняет состояние
    selected_tab = st.radio("Раздел:", tab_options, horizontal=True, label_visibility="collapsed")
    st.sidebar.caption("v2.3 (Multi-Venue) 🚀")
    st.write("---")

    # --- 1. ИНФЛЯЦИЯ ---
    if selected_tab == "🔥 Инфляция":
        st.subheader(f"🔥 Инфляционный Трекер (по состоянию на {target_date.strftime('%d.%m.%Y')})")
        
        # Ensure target_date is datetime for comparison
        if isinstance(target_date, datetime):
             target_ts = target_date
        else:
             target_ts = pd.to_datetime(target_date)

        df_inflation_scope = df_full[df_full['Дата_Отчета'] <= target_ts]
        price_history = df_inflation_scope.groupby(['Блюдо', 'Дата_Отчета'])['Unit_Cost'].mean().reset_index()
        unique_items = price_history['Блюдо'].unique()
        inflation_data = []
        total_gross_loss = 0
        total_gross_save = 0

        for item in unique_items:
            p_data = price_history[price_history['Блюдо'] == item].sort_values('Дата_Отчета')
            if len(p_data) > 1:
                first_price = p_data.iloc[0]['Unit_Cost']
                last_price = p_data.iloc[-1]['Unit_Cost']
                qty_sold = df_view[df_view['Блюдо'] == item]['Количество'].sum()

                if first_price > 5 and qty_sold > 0: 
                    diff_abs = last_price - first_price
                    diff_pct = (diff_abs / first_price) * 100
                    financial_impact = diff_abs * qty_sold
                    if financial_impact > 0: total_gross_loss += financial_impact
                    else: total_gross_save += abs(financial_impact)
                    if abs(diff_pct) > 1:
                        inflation_data.append({'Товар': item, 'Старая цена': first_price, 'Новая цена': last_price, 'Рост %': diff_pct, 'Эффект (₽)': financial_impact})
        
        net_result = total_gross_loss - total_gross_save
        inf1, inf2, inf3 = st.columns(3)
        inf1.metric("🔴 Потери (Инфляция)", f"-{total_gross_loss:,.0f} ₽")
        inf2.metric("🟢 Экономия (Скидки)", f"+{total_gross_save:,.0f} ₽")
        inf3.metric("🏁 Чистый Итог", f"-{net_result:,.0f} ₽" if net_result > 0 else f"+{abs(net_result):,.0f} ₽", delta_color="inverse")
        
        st.write("---")
        if inflation_data:
            df_inf = pd.DataFrame(inflation_data)
            col_up, col_down = st.columns(2)
            with col_up:
                st.write("### 🔺 Топ-30: Цена выросла (Убыток)")
                if not df_inf.empty:
                    df_up = df_inf.sort_values('Эффект (₽)', ascending=False).head(30)
                    st.dataframe(
                        df_up[['Товар', 'Рост %', 'Эффект (₽)']],
                        column_config={
                            "Рост %": st.column_config.NumberColumn(format="+%.1f %%"),
                            "Эффект (₽)": st.column_config.NumberColumn(format="%.0f ₽"),
                        },
                        use_container_width=True
                    )
            with col_down:
                st.write("### 🔻 Топ-30: Цена упала (Экономия)")
                if not df_inf.empty:
                    df_down = df_inf.sort_values('Эффект (₽)', ascending=True).head(30)
                    st.dataframe(
                        df_down[['Товар', 'Рост %', 'Эффект (₽)']],
                        column_config={
                            "Рост %": st.column_config.NumberColumn(format="%.1f %%"),
                            "Эффект (₽)": st.column_config.NumberColumn(format="%.0f ₽"),
                        },
                        use_container_width=True
                    )
        else:
            st.success("Цены стабильны.")

    # --- 2. ДИНАМИКА И ПОСТАВЩИКИ ---
    elif selected_tab == "📉 Динамика и Поставщики":
        st.subheader("📉 История цен и Рейтинг Поставщиков")
        
        c_dyn1, c_dyn2 = st.columns([2, 1])
        
        with c_dyn1:
            st.write("### 🔍 Как менялась цена закупки?")
            all_items = sorted(df_full['Блюдо'].unique())
            selected_item = st.selectbox("Выберите товар/блюдо:", all_items)
            item_data = df_full[df_full['Блюдо'] == selected_item].sort_values('Дата_Отчета')
            
            if not item_data.empty:
                fig_trend = px.line(item_data, x='Дата_Отчета', y='Unit_Cost', markers=True, 
                                    title=f"Динамика цены: {selected_item}",
                                    labels={'Unit_Cost': 'Цена закупки (₽)', 'Дата_Отчета': 'Дата'})
                st.plotly_chart(update_chart_layout(fig_trend), use_container_width=True)
                
                # БЕЗОПАСНЫЙ ВЫВОД ТАБЛИЦЫ
                cols_to_show = ['Дата_Отчета', 'Unit_Cost']
                if 'Поставщик' in item_data.columns:
                    cols_to_show.append('Поставщик')
                
                st.dataframe(
                    item_data[cols_to_show],
                    column_config={
                        "Unit_Cost": st.column_config.NumberColumn(format="%.2f ₽"),
                        "Дата_Отчета": st.column_config.DateColumn(format="DD.MM.YYYY"),
                    },
                    use_container_width=True
                )
            else:
                st.warning("Нет данных по этому товару.")

        with c_dyn2:
            st.write("### 🏆 Топ Поставщиков")
            # Проверяем наличие колонки перед группировкой
            if 'Поставщик' in df_view.columns:
                supplier_stats = df_view.groupby('Поставщик')['Себестоимость'].sum().reset_index()
                supplier_stats = supplier_stats[supplier_stats['Поставщик'] != 'Не указан'].sort_values('Себестоимость', ascending=False).head(10)
                
                if not supplier_stats.empty:
                    fig_sup = px.bar(supplier_stats, x='Себестоимость', y='Поставщик', orientation='h', text_auto='.0s', color='Себестоимость')
                    st.plotly_chart(update_chart_layout(fig_sup), use_container_width=True)
                else:
                    st.info("Данные по поставщикам не найдены.")
            else:
                st.info("В загруженных файлах нет колонки 'Поставщик'.")

    # --- 3. МЕНЮ И КОСТЫ ---
    elif selected_tab == "🍰 Меню и Косты":
        view_mode = st.radio("Детализация категорий:", ["🔍 Укрупненно (Макро-группы)", "🔬 Детально (Микро-категории)"], horizontal=True)
        target_cat = 'Макро_Категория' if 'Макро' in view_mode else 'Категория'

        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Структура выручки")
            df_cat = df_view.groupby(target_cat)['Выручка с НДС'].sum().reset_index()
            fig_pie = px.pie(df_cat, values='Выручка с НДС', names=target_cat, hole=0.4)
            fig_pie.update_traces(hovertemplate='%{label}: %{value:,.0f} ₽ (%{percent})')
            st.plotly_chart(update_chart_layout(fig_pie), use_container_width=True)
        
        with c2:
            st.subheader("📊 Детальный анализ Фуд-коста")
            df_menu = df_view.groupby(['Блюдо', target_cat]).agg({'Выручка с НДС': 'sum', 'Себестоимость': 'sum', 'Количество': 'sum'}).reset_index()
            df_menu['Фудкост %'] = np.where(df_menu['Выручка с НДС']>0, df_menu['Себестоимость']/df_menu['Выручка с НДС']*100, 0)
            df_menu = df_menu.sort_values('Выручка с НДС', ascending=False).head(50)
            df_menu = df_menu.rename(columns={target_cat: 'Категория'})
            
            # Highlight High FC > 26%
            def highlight_fc(s):
                return ['color: #FF4B4B; font-weight: bold' if v > 26 else '' for v in s]

            st.dataframe(
                df_menu.style.apply(highlight_fc, subset=['Фудкост %'], axis=0).format(precision=1),
                column_config={
                    "Выручка с НДС": st.column_config.NumberColumn(format="%.0f ₽"),
                    "Фудкост %": st.column_config.NumberColumn(format="%.1f %%"),
                },
                use_container_width=True,
                height=400
            )

        # --- VISUAL CATEGORY EDITOR (Relocated) ---
        st.write("---")
        st.subheader("🛠 Разбор нераспознанных блюд ('Прочее')")
        
        # Find items in "Other" based on current df_items (which is scoped by date/venue)
        # OR better: use global df_full to find ALL unmapped items to fix them once
        other_items_global = st.session_state.df_full[st.session_state.df_full['Категория'] == '📦 Прочее']['Блюдо'].unique()
        
        if len(other_items_global) > 0:
            st.warning(f"Найдено {len(other_items_global)} блюд в категории 'Прочее'. Давайте их распределим!")
            
            # 1. Prepare Categories List
            standard_cats = [
                "⛔ Исключить из отчетов", # NEW: Special category to hide item
                "🍔 Еда (Кухня)", "🍹 Коктейли", "☕ Кофе", "🍵 Чай", "🍺 Пиво Розлив", "💧 Водка",
                "🍷 Вино", "🥤 Стекло/Банка Б/А", "🚰 Розлив Б/А", "🍓 Милк/Фреш/Смузи", 
                "🍏 Сидр ШТ", "🍾 Пиво ШТ", "🥃 Виски", "💧 Водка", "🏴‍☠️ Ром", 
                "🌵 Текила", "🌲 Джин", "🍇 Коньяк/Бренди", "🍒 Ликер/Настойка", "🍬 Доп. ингредиенты"
            ]
            existing_cats = [c for c in st.session_state.df_full['Категория'].unique() if c != '📦 Прочее']
            all_options = sorted(list(set(standard_cats + existing_cats)))

            # 2. Prepare Data for Editor
            df_to_edit = pd.DataFrame({'Блюдо': other_items_global, 'Категория': '📦 Прочее'})

            # 3. Render Editor
            edited_df = st.data_editor(
                df_to_edit,
                column_config={
                    "Блюдо": st.column_config.TextColumn("Блюдо", disabled=True),
                    "Категория": st.column_config.SelectboxColumn(
                        "Выберите категорию",
                        options=all_options,
                        required=True
                    )
                },
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                key="editor_changes_tab"
            )

            # 4. Save Logic
            if st.button("💾 Сохранить изменения (Меню)"):
                changed_rows = edited_df[edited_df['Категория'] != '📦 Прочее']
                if not changed_rows.empty:
                    new_map = dict(zip(changed_rows['Блюдо'], changed_rows['Категория']))
                    # Assuming save_custom_categories and load_custom_categories are defined elsewhere or need to be added
                    # For this specific instruction, I'll assume they are available or will be added by the user.
                    # If not, this part would cause an error.
                    # Placeholder for actual save/load logic if not defined:
                    # save_custom_categories(new_map) 
                    # st.session_state.custom_cats = load_custom_categories() 
                    save_custom_categories(new_map)
                    st.cache_data.clear()
                    st.success(f"✅ Сохранено {len(new_map)} исправлений! Перезагружаю...")
                    st.rerun()
                else:
                    st.warning("⚠️ Вы не выбрали новые категории.")
        else:
            st.success("🎉 Все блюда распознаны! Нет позиций в 'Прочее'.")
        


    # --- 4. ABC МАТРИЦА ---
    elif selected_tab == "⭐ Матрица (ABC)":
        st.subheader("⭐ Матрица Меню (ABC)")
        col_L1, col_L2, col_L3, col_L4 = st.columns(4)
        col_L1.info("⭐ **Звезды**\n\nВысокая маржа, Популярные.\n(Син)")
        col_L2.warning("🐎 **Лошадки**\n\nНизкая маржа, Популярные.\n(Жел)")
        col_L3.success("❓ **Загадки**\n\nВысокая маржа, Мало продаж.\n(Зел)")
        col_L4.error("🐶 **Собаки**\n\nНизкая маржа, Мало продаж.\n(Крас)")

        abc_df = df_view.groupby('Блюдо').agg({'Количество': 'sum', 'Выручка с НДС': 'sum', 'Себестоимость': 'sum'}).reset_index()
        abc_df = abc_df[abc_df['Количество'] > 0]
        abc_df['Маржа'] = abc_df['Выручка с НДС'] - abc_df['Себестоимость']
        abc_df['Unit_Margin'] = abc_df['Маржа'] / abc_df['Количество']
        avg_qty = abc_df['Количество'].mean()
        avg_margin = abc_df['Unit_Margin'].mean()
        
        def classify_abc(row):
            if row['Unit_Margin'] >= avg_margin and row['Количество'] >= avg_qty: return "⭐ Звезда"
            if row['Unit_Margin'] < avg_margin and row['Количество'] >= avg_qty: return "🐎 Лошадка"
            if row['Unit_Margin'] >= avg_margin and row['Количество'] < avg_qty: return "❓ Загадка"
            return "🐶 Собака"

        abc_df['Класс'] = abc_df.apply(classify_abc, axis=1)
        # Исправленные цвета: Звезды=Синий, Лошадки=Золотой, Загадки=Зеленый, Собаки=Красный
        fig_abc = px.scatter(abc_df, x="Количество", y="Unit_Margin", color="Класс", hover_name="Блюдо", size="Выручка с НДС", 
                             color_discrete_map={"⭐ Звезда": "blue", "🐎 Лошадка": "gold", "❓ Загадка": "green", "🐶 Собака": "red"}, log_x=True)
        fig_abc.update_traces(hovertemplate='<b>%{hovertext}</b><br>Продажи: %{x} шт<br>Маржа с блюда: %{y:.0f} ₽')
        fig_abc.add_vline(x=avg_qty, line_dash="dash", line_color="gray")
        fig_abc.add_hline(y=avg_margin, line_dash="dash", line_color="gray")
        st.plotly_chart(update_chart_layout(fig_abc), use_container_width=True)

    # --- 5. ДНИ НЕДЕЛИ ---
    elif selected_tab == "🗓 Дни недели":
        st.subheader("🗓 Дни недели")
        if len(dates_list) > 1:
            df_full['ДеньНедели'] = df_full['Дата_Отчета'].dt.day_name()
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            days_rus = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
            dow_stats = df_full.groupby(['Дата_Отчета', 'ДеньНедели'])['Выручка с НДС'].sum().reset_index().groupby('ДеньНедели')['Выручка с НДС'].mean().reindex(days_order).reset_index()
            dow_stats['ДеньРус'] = days_rus
            fig_dow = px.bar(dow_stats, x='ДеньРус', y='Выручка с НДС', color='Выручка с НДС')
            fig_dow.update_traces(texttemplate='%{y:,.0f} ₽', textposition='auto')
            st.plotly_chart(update_chart_layout(fig_dow), use_container_width=True)
        else:
            st.warning("Мало данных.")

    # --- 6. ПЛАН ЗАКУПОК ---
    elif selected_tab == "📦 План Закупок":
        st.subheader("📦 Калькулятор Закупки")
        c_set1, c_set2 = st.columns(2)
        days_to_buy = c_set1.slider("📅 Дней закупки", 1, 14, 3)
        safety_stock = c_set2.slider("🛡 Запас (%)", 0, 50, 10)
        
        last_30_days = df_full['Дата_Отчета'].max() - timedelta(days=30)
        df_recent = df_full[df_full['Дата_Отчета'] >= last_30_days]
        daily_sales = df_recent.groupby('Блюдо')['Количество'].sum().reset_index()
        daily_sales['Avg_Daily_Qty'] = daily_sales['Количество'] / 30
        last_prices = df_full.sort_values('Дата_Отчета').groupby('Блюдо')['Unit_Cost'].last().reset_index()
        plan_df = pd.merge(daily_sales[['Блюдо', 'Avg_Daily_Qty']], last_prices, on='Блюдо')
        
        plan_df['Need_Qty'] = plan_df['Avg_Daily_Qty'] * days_to_buy * (1 + safety_stock/100)
        plan_df['Budget'] = plan_df['Need_Qty'] * plan_df['Unit_Cost']
        plan_df = plan_df[plan_df['Need_Qty'] > 0.5].sort_values('Budget', ascending=False)
        
        st.metric("💰 Бюджет", f"{plan_df['Budget'].sum():,.0f} ₽")
        st.dataframe(
            plan_df[['Блюдо', 'Unit_Cost', 'Need_Qty', 'Budget']],
            column_config={
                "Unit_Cost": st.column_config.NumberColumn(format="%.1f ₽"),
                "Need_Qty": st.column_config.NumberColumn(format="%.1f"),
                "Budget": st.column_config.NumberColumn(format="%.0f ₽"),
            },
            use_container_width=True
        )

    # --- 7. СИМУЛЯТОР ---
    elif selected_tab == "🔮 Симулятор":
        st.subheader("🔮 Симулятор: Анализ 'Что если?'")
        st.info("Экспериментируйте с ценами и затратами, чтобы увидеть, как изменится ваша прибыль.")
        
        col_input, col_result = st.columns([1, 2])
        
        with col_input:
            st.write("### 🎛 Настройки")
            
            # 1. Выбор категорий
            all_cats = sorted(df_full['Категория'].dropna().unique())
            selected_cats = st.multiselect("Выберите категории:", all_cats, default=all_cats[:3] if len(all_cats) > 3 else all_cats)
            
            if not selected_cats:
                st.warning("👈 Выберите хотя бы одну категорию.")
            else:
                st.markdown("---")
                st.write("**Параметры моделирования:**")
                
                delta_price = st.slider("💰 Изменить Цену продажи (%)", -50, 50, 0, step=1, help="Насколько мы поднимем или опустим цены в меню")
                delta_cost = st.slider("📉 Изменить Себестоимость (%)", -50, 50, 0, step=1, help="Если поставщики поднимут цены")
                delta_vol = st.slider("🛒 Эластичность спроса (Продажи %)", -50, 50, 0, step=1, help="Как изменится количество чеков (обычно если цена растет, продажи падают)")

        with col_result:
            if selected_cats:
                # Фильтрация данных
                df_sim = df_view[df_view['Категория'].isin(selected_cats)].copy()
                
                # Базовые показатели
                base_revenue = df_sim['Выручка с НДС'].sum()
                base_cost_total = df_sim['Себестоимость'].sum()
                base_margin = base_revenue - base_cost_total
                base_qty = df_sim['Количество'].sum()
                
                # Симуляция
                # Новая цена = Старая цена * (1 + %) -> Новая выручка на ед. = Старая выручка * (1 + %)
                # Новая с/с = Старая с/с * (1 + %)
                # Новое кол-во = Старое кол-во * (1 + %)
                
                sim_revenue = base_revenue * (1 + delta_price/100) * (1 + delta_vol/100)
                sim_cost_total = base_cost_total * (1 + delta_cost/100) * (1 + delta_vol/100)
                sim_margin = sim_revenue - sim_cost_total
                
                # Дельты
                diff_rev = sim_revenue - base_revenue
                diff_margin = sim_margin - base_margin
                
                st.write(f"### 📊 Прогноз результата (Категории: {len(selected_cats)})")
                
                # Метрики
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("Выручка (Sim)", f"{sim_revenue:,.0f} ₽", f"{diff_rev:+,.0f} ₽")
                kpi2.metric("Маржа (Sim)", f"{sim_margin:,.0f} ₽", f"{diff_margin:+,.0f} ₽")
                
                new_profitability = (sim_margin / sim_revenue * 100) if sim_revenue > 0 else 0
                old_profitability = (base_margin / base_revenue * 100) if base_revenue > 0 else 0
                kpi3.metric("Рентабельность", f"{new_profitability:.1f}%", f"{new_profitability - old_profitability:+.1f}%")
                
                st.markdown("---")
                
                # График сравнения
                st.write("#### ⚖️ Сравнение: До и После")
                
                comp_data = [
                    {'Показатель': 'Выручка', 'Сценарий': 'Было', 'Сумма': base_revenue},
                    {'Показатель': 'Выручка', 'Сценарий': 'Станет', 'Сумма': sim_revenue},
                    {'Показатель': 'Маржа (Прибыль)', 'Сценарий': 'Было', 'Сумма': base_margin},
                    {'Показатель': 'Маржа (Прибыль)', 'Сценарий': 'Станет', 'Сумма': sim_margin},
                ]
                df_comp = pd.DataFrame(comp_data)
                
                fig_comp = px.bar(df_comp, x='Показатель', y='Сумма', color='Сценарий', barmode='group', 
                                  color_discrete_map={'Было': 'gray', 'Станет': 'blue' if diff_margin >= 0 else 'red'})
                fig_comp.update_traces(texttemplate='%{y:,.0f} ₽', textposition='auto')
                st.plotly_chart(update_chart_layout(fig_comp), use_container_width=True)
                
                if diff_margin > 0:
                    st.success(f"🚀 Отличный сценарий! Вы заработаете на **{diff_margin:,.0f} ₽** больше.")
                elif diff_margin < 0:
                    st.error(f"⚠️ Осторожно! Это приведет к убыткам в размере **{abs(diff_margin):,.0f} ₽**.")
                else:
                    st.info("Никаких изменений.")

else:
    st.info("👈 Загрузите данные.")
