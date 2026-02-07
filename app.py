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

# --- СПИСОК ИСКЛЮЧЕНИЙ ---
IGNORE_NAMES = [
    "Бар Место", "Бар Место Бургерная", "Итого", "Номенклатура", "Склады", 
    "Незавершённое производство", "Товары"
]

# --- ИНИЦИАЛИЗАЦИЯ ПАМЯТИ ---
if 'df_full' not in st.session_state:
    st.session_state.df_full = None

# --- СЛОВАРЬ КАТЕГОРИЙ (ЛОВЕЦ СЛОВ) ---
def detect_category(name_input):
    name = str(name_input).lower()
    rules = {
        '🍺 Пиво/Сидр': ['пиво', 'beer', 'ale', 'ipa', 'apa', 'lager', 'stout', 'сидр', 'cidre', 'heineken', 'guinness', 'эль', 'стаут', 'лагер'],
        '🍷 Вино': ['вино', 'wine', 'red', 'white', 'rose', 'шардоне', 'мерло', 'рислинг', 'пино', 'совиньон', 'кьянти', 'брют', 'просекко', 'cava'],
        '🥃 Крепкое': ['водка', 'vodka', 'виски', 'whiskey', 'whisky', 'ром', 'rum', 'джин', 'gin', 'коньяк', 'cognac', 'текила', 'настойка', 'егерь', 'jager'],
        '🍹 Коктейли': ['коктейль', 'long', 'shot', 'апероль', 'мохито', 'физ', 'сауэр', 'негрони', 'джин-тоник', 'шприц'],
        '☕ Безалкогольное': ['вода', 'water', 'сока', 'juice', 'кофе', 'чай', 'tea', 'lemonade', 'лимонад', 'cola', 'tonic', 'тоник', 'коле', 'эспрессо', 'капучино'],
        '🍔 Еда (Кухня)': ['бургер', 'суп', 'салат', 'фри', 'сыр', 'мясо', 'стейк', 'хлеб', 'соус', 'картофель', 'гренки', 'крылья', 'креветки', 'паста', 'сухарики']
    }
    for category, keywords in rules.items():
        if any(word in name for word in keywords):
            return category
    return '📦 Прочее'

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
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
        # 1. Попытка прочитать дату из заголовка (первые 10 строк)
        if isinstance(file_content, BytesIO): file_content.seek(0)
        try:
            df_raw = pd.read_csv(file_content, header=None, nrows=10, sep=None, engine='python')
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df_raw = pd.read_excel(file_content, header=None, nrows=10)

        header_text = " ".join(df_raw.iloc[0:10, 0].astype(str).tolist())
        report_date = parse_russian_date(header_text)
        
        # 2. Если в файле нет даты, ищем в имени файла
        if not report_date:
            month_map = {
                'jan': 'января', 'feb': 'февраля', 'mar': 'марта', 'apr': 'апреля',
                'may': 'мая', 'jun': 'июня', 'jul': 'июля', 'aug': 'августа',
                'sep': 'сентября', 'oct': 'октября', 'nov': 'ноября', 'dec': 'декабря'
            }
            for eng, rus in month_map.items():
                if eng in filename.lower():
                     d_match = re.search(r'(\d{1,2})', filename)
                     if d_match:
                         # Используем ТЕКУЩИЙ год
                         current_year = datetime.now().year
                         report_date = datetime(current_year, RUS_MONTHS[rus], int(d_match.group(1)))
                         break
        
        if not report_date: report_date = datetime.now()

        # 3. Чтение таблицы данных
        if isinstance(file_content, BytesIO): file_content.seek(0)
        try:
            df = pd.read_csv(file_content, header=5, sep=None, engine='python')
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df = pd.read_excel(file_content, header=5)

        df.columns = df.columns.str.strip()
        if 'Выручка с НДС' not in df.columns: return None

        col_name = df.columns[0] # "Склады" / "Номенклатура"
        df = df.dropna(subset=[col_name])
        
        # Фильтрация мусора
        df = df[~df[col_name].astype(str).str.strip().isin(IGNORE_NAMES)]
        df = df[~df[col_name].astype(str).str.contains("Итого", case=False)]
        
        cols_to_num = ['Количество', 'Себестоимость', 'Выручка с НДС']
        for col in cols_to_num:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Расчетные метрики
        df['Unit_Cost'] = np.where(df['Количество'] != 0, df['Себестоимость'] / df['Количество'], 0)
        df['Фудкост'] = np.where(df['Выручка с НДС'] > 0, (df['Себестоимость'] / df['Выручка с НДС'] * 100), 0)
        
        df['Дата_Отчета'] = report_date
        df = df.rename(columns={col_name: 'Блюдо'})
        
        # Добавляем категорию сразу при загрузке
        df['Категория'] = df['Блюдо'].apply(detect_category)
        
        return df
    except Exception:
        return None

# --- ЗАГРУЗКА ЯНДЕКС (КЭШИРОВАНИЕ) ---
@st.cache_data(ttl=3600, show_spinner="Скачиваем данные с Яндекс.Диска...")
def load_all_from_yandex(folder_path):
    token = st.secrets.get("YANDEX_TOKEN")
    if not token: return None
    
    headers = {'Authorization': f'OAuth {token}'}
    api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
    params = {'path': folder_path, 'limit': 2000} # Лимит 2000 файлов
    
    try:
        response = requests.get(api_url, headers=headers, params=params)
        if response.status_code != 200: return []
            
        items = response.json().get('_embedded', {}).get('items', [])
        files = [i for i in items if i['type'] == 'file']
        
        data_frames = []
        for item in files:
            try:
                file_resp = requests.get(item['file'], headers=headers)
                df = process_single_file(BytesIO(file_resp.content), filename=item['name'])
                if df is not None: data_frames.append(df)
            except Exception: continue
        return data_frames
    except Exception: return []

# --- SIDEBAR: УПРАВЛЕНИЕ ---
st.sidebar.header("📂 Управление")
source_mode = st.sidebar.radio("Источник:", ["Яндекс.Диск", "Ручная загрузка"])

if st.sidebar.button("🗑 Сбросить кэш"):
    st.cache_data.clear()
    st.session_state.df_full = None
    st.rerun()

if source_mode == "Ручная загрузка":
    uploaded_files = st.sidebar.file_uploader("Файлы отчетов", accept_multiple_files=True)
    if uploaded_files:
        temp_data = []
        for f in uploaded_files:
            df = process_single_file(f, f.name)
            if df is not None: temp_data.append(df)
        if temp_data:
            st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')

elif source_mode == "Яндекс.Диск":
    yandex_path = st.sidebar.text_input("Папка:", "Отчеты_Ресторан")
    if st.sidebar.button("🔄 Скачать данные"):
        if not st.secrets.get("YANDEX_TOKEN"):
             st.error("⚠️ Нет токена в Secrets!")
        else:
            temp_data = load_all_from_yandex(yandex_path)
            if temp_data:
                st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')
                st.success(f"Загружено {len(temp_data)} отчетов!")
            else:
                st.warning("Файлов не найдено.")

# --- ОСНОВНАЯ АНАЛИТИКА ---
if st.session_state.df_full is not None:
    df_full = st.session_state.df_full
    
    # Кнопка экспорта в Excel
    with st.sidebar:
        st.write("---")
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_full.to_excel(writer, sheet_name='Data', index=False)
        st.download_button(
            label="📥 Скачать Excel",
            data=buffer.getvalue(),
            file_name=f"Analytics_{datetime.now().date()}.xlsx",
            mime="application/vnd.ms-excel"
        )

    # Фильтр дат
    dates_list = sorted(df_full['Дата_Отчета'].unique(), reverse=True)
    date_str_list = [d.strftime('%d.%m.%Y') for d in dates_list]
    date_options = ["📅 ВСЕ ВРЕМЯ (Сводный)"] + date_str_list
    
    st.write("---")
    col_sel1, col_sel2 = st.columns([1, 4])
    selected_option = col_sel1.selectbox("Период:", date_options)
    
    # Подготовка данных в зависимости от выбора
    if "ВСЕ ВРЕМЯ" in selected_option:
        df_view = df_full
        period_title = "За все время"
    else:
        current_date = datetime.strptime(selected_option, '%d.%m.%Y')
        df_view = df_full[df_full['Дата_Отчета'] == current_date]
        period_title = selected_option

    # === KPI МЕТРИКИ ===
    total_rev = df_view['Выручка с НДС'].sum()
    total_cost = df_view['Себестоимость'].sum()
    avg_fc = (total_cost / total_rev * 100) if total_rev > 0 else 0
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("💰 Выручка", f"{total_rev:,.0f} ₽")
    kpi2.metric("📉 Фуд-кост", f"{avg_fc:.1f}%")
    kpi3.metric("💳 Маржа", f"{(total_rev - total_cost):,.0f} ₽")
    kpi4.metric("🧾 Позиций", len(df_view))

    # === ВКЛАДКИ АНАЛИТИКИ ===
    tab1, tab2, tab3, tab4 = st.tabs([
        "🍰 Меню и Категории", 
        "⭐ Матрица Меню (ABC)", 
        "🗓 Дни недели", 
        "🔥 Инфляция и Цены"
    ])

    # 1. ОБЗОР И КАТЕГОРИИ
    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Структура выручки")
            df_cat = df_view.groupby('Категория')['Выручка с НДС'].sum().reset_index()
            fig_pie = px.pie(df_cat, values='Выручка с НДС', names='Категория', hole=0.4)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with c2:
            st.subheader("Топ-10 Блюд по выручке")
            top_items = df_view.groupby('Блюдо')[['Выручка с НДС', 'Фудкост']].sum().reset_index().sort_values('Выручка с НДС', ascending=False).head(10)
            # Пересчитываем фудкост для агрегированных данных
            # (так как просто сумма фудкоста неправильна, нужно средневзвешенное, но для топа за день сойдет сумма выручки)
            st.plotly_chart(px.bar(top_items, x='Выручка с НДС', y='Блюдо', orientation='h',
                            color='Выручка с НДС', color_continuous_scale='Viridis'), use_container_width=True)

    # 2. ABC МАТРИЦА (МЕНЮ ИНЖИНИРИНГ)
    with tab2:
        st.subheader("Матрица Меню (Kasavana-Smith)")
        st.info("💡 **Ось X:** Популярность (шт) | **Ось Y:** Маржа с блюда (руб)")
        
        # Группируем данные по блюдам для матрицы
        abc_df = df_view.groupby('Блюдо').agg({
            'Количество': 'sum',
            'Выручка с НДС': 'sum',
            'Себестоимость': 'sum',
            'Категория': 'first'
        }).reset_index()
        
        abc_df = abc_df[abc_df['Количество'] > 0]
        abc_df['Маржа'] = abc_df['Выручка с НДС'] - abc_df['Себестоимость']
        abc_df['Unit_Margin'] = abc_df['Маржа'] / abc_df['Количество']
        
        # Средние значения (оси матрицы)
        avg_qty = abc_df['Количество'].mean()
        avg_margin = abc_df['Unit_Margin'].mean()
        
        # Классификация
        def classify_abc(row):
            high_margin = row['Unit_Margin'] >= avg_margin
            high_pop = row['Количество'] >= avg_qty
            if high_margin and high_pop: return "⭐ Звезда"
            if not high_margin and high_pop: return "🐎 Лошадка"
            if high_margin and not high_pop: return "❓ Загадка"
            return "🐶 Собака"

        abc_df['Класс'] = abc_df.apply(classify_abc, axis=1)
        
        fig_abc = px.scatter(abc_df, x="Количество", y="Unit_Margin", color="Класс",
                             hover_name="Блюдо", size="Выручка с НДС",
                             color_discrete_map={"⭐ Звезда": "gold", "🐎 Лошадка": "blue", "❓ Загадка": "green", "🐶 Собака": "red"},
                             log_x=True, title=f"Анализ меню ({len(abc_df)} позиций)")
        
        # Линии средних
        fig_abc.add_vline(x=avg_qty, line_dash="dash", line_color="gray", annotation_text="Ср. Популярность")
        fig_abc.add_hline(y=avg_margin, line_dash="dash", line_color="gray", annotation_text="Ср. Маржа")
        st.plotly_chart(fig_abc, use_container_width=True)
        
        with st.expander("🔍 Детальная таблица ABC"):
            st.dataframe(abc_df[['Блюдо', 'Класс', 'Количество', 'Unit_Margin', 'Выручка с НДС']].sort_values('Выручка с НДС', ascending=False), use_container_width=True)

    # 3. ДНИ НЕДЕЛИ
    with tab3:
        st.subheader("📅 Эффективность дней недели")
        if len(dates_list) > 1:
            df_full['ДеньНедели'] = df_full['Дата_Отчета'].dt.day_name()
            # Перевод на русский и сортировка
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            days_rus = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
            
            # Агрегация
            daily_stats = df_full.groupby(['Дата_Отчета', 'ДеньНедели'])['Выручка с НДС'].sum().reset_index()
            # Средняя выручка по дням недели
            dow_stats = daily_stats.groupby('ДеньНедели')['Выручка с НДС'].mean().reindex(days_order).reset_index()
            dow_stats['ДеньРус'] = days_rus
            
            fig_dow = px.bar(dow_stats, x='ДеньРус', y='Выручка с НДС', 
                             title="Средняя выручка по дням недели", 
                             color='Выручка с НДС', color_continuous_scale='Blues')
            st.plotly_chart(fig_dow, use_container_width=True)
        else:
            st.warning("Нужно загрузить данные за несколько дней для анализа недели.")

    # 4. ИНФЛЯЦИЯ (ТРЕКЕР ЦЕН)
    with tab4:
        st.subheader("🔥 Инфляционный Трекер (Топ-5 подорожавших)")
        st.write("Сравниваем самую первую цену закупки с самой последней.")
        
        price_history = df_full.groupby(['Блюдо', 'Дата_Отчета'])['Unit_Cost'].mean().reset_index()
        unique_items = price_history['Блюдо'].unique()
        inflation_data = []

        for item in unique_items:
            # Берем все записи по товару и сортируем по дате
            p_data = price_history[price_history['Блюдо'] == item].sort_values('Дата_Отчета')
            if len(p_data) > 1:
                first_price = p_data.iloc[0]['Unit_Cost']
                last_price = p_data.iloc[-1]['Unit_Cost']
                
                # Считаем только если цена была > 1 руб (защита от ошибок)
                if first_price > 1:
                    diff_pct = ((last_price - first_price) / first_price) * 100
                    diff_abs = last_price - first_price
                    # Фильтруем только подорожание более 1%
                    if diff_pct > 1:
                        inflation_data.append({
                            'Товар': item,
                            'Старая цена': first_price,
                            'Новая цена': last_price,
                            'Рост ₽': diff_abs,
                            'Рост %': diff_pct
                        })
        
        if inflation_data:
            df_inf = pd.DataFrame(inflation_data).sort_values('Рост %', ascending=False).head(10)
            
            # Красивое отображение
            st.dataframe(
                df_inf.style.format({
                    'Старая цена': "{:.1f} ₽", 
                    'Новая цена': "{:.1f} ₽", 
                    'Рост ₽': "+{:.1f} ₽", 
                    'Рост %': "+{:.1f}%"
                }).background_gradient(subset=['Рост %'], cmap='Reds'),
                use_container_width=True
            )
            
            # График топ-5
            top5 = df_inf.head(5)
            fig_inf = px.bar(top5, x='Товар', y='Рост %', color='Рост %', title="Лидеры подорожания", color_continuous_scale='Reds')
            st.plotly_chart(fig_inf, use_container_width=True)
        else:
            st.success("Существенного роста цен не обнаружено.")

else:
    st.info("👈 Загрузите данные через меню слева (Яндекс или Файлы), чтобы увидеть магию.")
