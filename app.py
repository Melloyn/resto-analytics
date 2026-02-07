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

# --- СПИСОК ИСКЛЮЧЕНИЙ (ТЕХНИЧЕСКИЕ СТРОКИ) ---
IGNORE_NAMES = [
    "Бар Место", "Бар Место Бургерная", "Итого", "Номенклатура", "Склады", 
    "Незавершённое производство", "Товары", "Услуги"
]

# --- КАТЕГОРИЗАТОР (ПО КЛЮЧЕВЫМ СЛОВАМ) ---
def detect_category(name_input):
    name = str(name_input).lower()
    
    rules = {
        '🍺 Пиво/Сидр': [
            'пиво', 'beer', 'ale', 'ipa', 'apa', 'lager', 'stout', 'сидр', 'cidre', 
            'heineken', 'guinness', 'эль', 'стаут', 'лагер', 'corona', 'spaten', 
            'bud', 'klosterbrau', 'blanche', 'filter', 'dark', 'нефильтр'
        ],
        '🍷 Вино': [
            'вино', 'wine', 'red', 'white', 'rose', 'шардоне', 'мерло', 'рислинг', 
            'пино', 'совиньон', 'кьянти', 'брют', 'просекко', 'cava', 'chardonnay', 
            'merlot', 'pinot', 'sauvignon', 'chianti', 'prosecco', 'riesling', 'shiraz'
        ],
        '🥃 Крепкое': [
            'водка', 'vodka', 'виски', 'whiskey', 'whisky', 'ром', 'rum', 'джин', 'gin', 
            'коньяк', 'cognac', 'текила', 'настойка', 'егерь', 'jager', 'jameson', 
            'jack', 'daniels', 'jim beam', 'macallan', 'absolut', 'finlandia', 'beluga', 
            'olmeca', 'martini', 'baileys', 'sambuca', 'absinthe'
        ],
        '🍹 Коктейли': [
            'коктейль', 'long', 'shot', 'апероль', 'мохито', 'физ', 'сауэр', 'негрони', 
            'джин-тоник', 'шприц', 'b-52', 'daiquiri', 'margarita', 'cosmopolitan'
        ],
        '☕ Безалкогольное': [
            'вода', 'water', 'сока', 'juice', 'кофе', 'чай', 'tea', 'lemonade', 
            'лимонад', 'cola', 'tonic', 'тоник', 'коле', 'эспрессо', 'капучино', 
            'bonaqua', 'rich', 'schweppes', 'латте', 'americano', 'red bull'
        ],
        '🍔 Еда (Кухня)': [
            'бургер', 'суп', 'салат', 'фри', 'сыр', 'мясо', 'стейк', 'хлеб', 'соус', 
            'картофель', 'гренки', 'крылья', 'креветки', 'паста', 'сухарики', 'сэндвич', 
            'добавка', 'десерт', 'мороженое', 'чизкейк', 'начос', 'кесадилья'
        ]
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
        # 1. Чтение даты из заголовка
        if isinstance(file_content, BytesIO): file_content.seek(0)
        try:
            df_raw = pd.read_csv(file_content, header=None, nrows=10, sep=None, engine='python')
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df_raw = pd.read_excel(file_content, header=None, nrows=10)

        header_text = " ".join(df_raw.iloc[0:10, 0].astype(str).tolist())
        report_date = parse_russian_date(header_text)
        
        # 2. Если даты нет, ищем в названии файла
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
                         current_year = datetime.now().year # ТЕКУЩИЙ ГОД
                         report_date = datetime(current_year, RUS_MONTHS[rus], int(d_match.group(1)))
                         break
        if not report_date: report_date = datetime.now()

        # 3. Чтение данных
        if isinstance(file_content, BytesIO): file_content.seek(0)
        try:
            df = pd.read_csv(file_content, header=5, sep=None, engine='python')
        except:
            if isinstance(file_content, BytesIO): file_content.seek(0)
            df = pd.read_excel(file_content, header=5)

        df.columns = df.columns.str.strip()
        if 'Выручка с НДС' not in df.columns: return None

        col_name = df.columns[0]
        df = df.dropna(subset=[col_name])
        
        # Фильтрация
        df = df[~df[col_name].astype(str).str.strip().isin(IGNORE_NAMES)]
        df = df[~df[col_name].astype(str).str.contains("Итого", case=False)]
        
        cols_to_num = ['Количество', 'Себестоимость', 'Выручка с НДС']
        for col in cols_to_num:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Расчеты
        df['Unit_Cost'] = np.where(df['Количество'] != 0, df['Себестоимость'] / df['Количество'], 0)
        df['Фудкост'] = np.where(df['Выручка с НДС'] > 0, (df['Себестоимость'] / df['Выручка с НДС'] * 100), 0)
        
        df['Дата_Отчета'] = report_date
        df = df.rename(columns={col_name: 'Блюдо'})
        df['Категория'] = df['Блюдо'].apply(detect_category)
        
        return df
    except Exception:
        return None

# --- ЗАГРУЗКА ЯНДЕКС (С КЭШЕМ) ---
@st.cache_data(ttl=3600, show_spinner="Скачиваем данные с Яндекс.Диска...")
def load_all_from_yandex(folder_path):
    token = st.secrets.get("YANDEX_TOKEN")
    if not token: return None
    
    headers = {'Authorization': f'OAuth {token}'}
    api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
    params = {'path': folder_path, 'limit': 2000} # Лимит 2000
    
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

# --- SIDEBAR ---
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

# --- АНАЛИТИКА ---
if st.session_state.df_full is not None:
    df_full = st.session_state.df_full
    
    # Кнопка экспорта (CSV всегда работает)
    with st.sidebar:
        st.write("---")
        csv = df_full.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Скачать базу (CSV)",
            data=csv,
            file_name=f"Analytics_{datetime.now().date()}.csv",
            mime="text/csv"
        )
        
        # Попытка Excel (если установлены библиотеки)
        try:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_full.to_excel(writer, sheet_name='Data', index=False)
            st.download_button(
                label="📥 Скачать базу (Excel)",
                data=buffer.getvalue(),
                file_name=f"Analytics_{datetime.now().date()}.xlsx",
                mime="application/vnd.ms-excel"
            )
        except Exception:
            st.caption("Excel экспорт недоступен, используйте CSV.")

    # Фильтр дат
    dates_list = sorted(df_full['Дата_Отчета'].unique(), reverse=True)
    date_str_list = [d.strftime('%d.%m.%Y') for d in dates_list]
    date_options = ["📅 ВСЕ ВРЕМЯ (Сводный)"] + date_str_list
    
    st.write("---")
    col_sel1, col_sel2 = st.columns([1, 4])
    selected_option = col_sel1.selectbox("Период:", date_options)
    
    if "ВСЕ ВРЕМЯ" in selected_option:
        df_view = df_full
    else:
        current_date = datetime.strptime(selected_option, '%d.%m.%Y')
        df_view = df_full[df_full['Дата_Отчета'] == current_date]

    # === KPI МЕТРИКИ ===
    total_rev = df_view['Выручка с НДС'].sum()
    total_cost = df_view['Себестоимость'].sum()
    avg_fc = (total_cost / total_rev * 100) if total_rev > 0 else 0
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("💰 Выручка", f"{total_rev:,.0f} ₽")
    kpi2.metric("📉 Фуд-кост", f"{avg_fc:.1f} %")
    kpi3.metric("💳 Маржа", f"{(total_rev - total_cost):,.0f} ₽")
    kpi4.metric("🧾 Позиций", len(df_view))

    # === ВКЛАДКИ ===
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔥 Инфляция и Цены",
        "🍰 Меню и Категории", 
        "⭐ Матрица Меню (ABC)", 
        "🗓 Дни недели"
    ])

    # 1. ИНФЛЯЦИЯ (ОБНОВЛЕННАЯ)
    with tab1:
        st.subheader("🔥 Инфляционный Трекер (Топ-20 изменений)")
        st.info("Сравнение цены закупки: Первая дата vs Последняя дата за выбранный период.")
        
        # Считаем среднюю цену закупа по дням
        price_history = df_full.groupby(['Блюдо', 'Дата_Отчета'])['Unit_Cost'].mean().reset_index()
        unique_items = price_history['Блюдо'].unique()
        inflation_data = []

        for item in unique_items:
            p_data = price_history[price_history['Блюдо'] == item].sort_values('Дата_Отчета')
            if len(p_data) > 1:
                first_price = p_data.iloc[0]['Unit_Cost']
                last_price = p_data.iloc[-1]['Unit_Cost']
                
                # Игнорируем технические позиции с ценой 0 или около 0
                if first_price > 1: 
                    diff_abs = last_price - first_price
                    diff_pct = (diff_abs / first_price) * 100
                    
                    # Фиксируем изменение более 1%
                    if abs(diff_pct) > 1:
                        inflation_data.append({
                            'Товар': item,
                            'Старая цена': first_price,
                            'Новая цена': last_price,
                            'Изменение ₽': diff_abs,
                            'Изменение %': diff_pct
                        })
        
        if inflation_data:
            df_inf = pd.DataFrame(inflation_data)
            # Сортируем по абсолютному значению % изменения (чтобы видеть и взлеты, и падения)
            df_inf['Abs_Change'] = df_inf['Изменение %'].abs()
            df_inf = df_inf.sort_values('Abs_Change', ascending=False).head(20)
            
            # Логика цветов:
            # Если цена ВЫРОСЛА (>0) -> Красный (плохо)
            # Если цена УПАЛА (<0) -> Зеленый (хорошо)
            def color_inflation(val):
                if val > 0:
                    return 'background-color: #ffcccc; color: black' # Красный
                elif val < 0:
                    return 'background-color: #ccffcc; color: black' # Зеленый
                return ''

            # Отображаем таблицу
            st.dataframe(
                df_inf[['Товар', 'Старая цена', 'Новая цена', 'Изменение ₽', 'Изменение %']].style
                .format({
                    'Старая цена': "{:.1f} ₽", 
                    'Новая цена': "{:.1f} ₽", 
                    'Изменение ₽': "{:+.1f} ₽", 
                    'Изменение %': "{:+.1f} %"
                })
                .map(color_inflation, subset=['Изменение %', 'Изменение ₽']),
                use_container_width=True
            )
        else:
            st.success("Цены стабильны (нет изменений более 1%).")

    # 2. ОБЗОР И КАТЕГОРИИ
    with tab2:
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
            st.plotly_chart(px.bar(top_items, x='Выручка с НДС', y='Блюдо', orientation='h', text_auto='.0f',
                            color='Выручка с НДС', color_continuous_scale='Viridis'), use_container_width=True)

    # 3. ABC МАТРИЦА
    with tab3:
        st.subheader("⭐ Матрица Меню (ABC)")
        st.info("Помогает понять, какие блюда приносят деньги, а какие тянут вниз.")
        
        abc_df = df_view.groupby('Блюдо').agg({
            'Количество': 'sum',
            'Выручка с НДС': 'sum',
            'Себестоимость': 'sum'
        }).reset_index()
        
        abc_df = abc_df[abc_df['Количество'] > 0]
        abc_df['Маржа'] = abc_df['Выручка с НДС'] - abc_df['Себестоимость']
        abc_df['Unit_Margin'] = abc_df['Маржа'] / abc_df['Количество']
        
        avg_qty = abc_df['Количество'].mean()
        avg_margin = abc_df['Unit_Margin'].mean()
        
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
                             log_x=True, title=f"Анализ меню (Ср. маржа: {avg_margin:.0f} ₽)")
        
        fig_abc.update_layout(yaxis_tickformat = '.0f', xaxis_title="Популярность (шт)", yaxis_title="Маржа с блюда (₽)")
        fig_abc.add_vline(x=avg_qty, line_dash="dash", line_color="gray", annotation_text="Ср. Поп.")
        fig_abc.add_hline(y=avg_margin, line_dash="dash", line_color="gray", annotation_text="Ср. Маржа")
        st.plotly_chart(fig_abc, use_container_width=True)

    # 4. ДНИ НЕДЕЛИ
    with tab4:
        st.subheader("🗓 Эффективность дней недели")
        if len(dates_list) > 1:
            df_full['ДеньНедели'] = df_full['Дата_Отчета'].dt.day_name()
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            days_rus = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
            
            daily_stats = df_full.groupby(['Дата_Отчета', 'ДеньНедели'])['Выручка с НДС'].sum().reset_index()
            dow_stats = daily_stats.groupby('ДеньНедели')['Выручка с НДС'].mean().reindex(days_order).reset_index()
            dow_stats['ДеньРус'] = days_rus
            
            fig_dow = px.bar(dow_stats, x='ДеньРус', y='Выручка с НДС', 
                             title="Средняя выручка по дням", 
                             text_auto='.0f',
                             color='Выручка с НДС', color_continuous_scale='Blues')
            fig_dow.update_layout(yaxis_tickformat = '0f')
            st.plotly_chart(fig_dow, use_container_width=True)
        else:
            st.warning("Загрузите отчеты за разные дни, чтобы увидеть статистику по неделям.")

else:
    st.info("👈 Загрузите данные через меню слева (Яндекс или Файлы).")
