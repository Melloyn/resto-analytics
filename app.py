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

# --- ИНИЦИАЛИЗАЦИЯ ПАМЯТИ ---
if 'df_full' not in st.session_state:
    st.session_state.df_full = None

# --- СПИСОК ИСКЛЮЧЕНИЙ ---
IGNORE_NAMES = [
    "Бар Место", "Бар Место Бургерная", "Итого", "Номенклатура", "Склады", 
    "Незавершённое производство", "Товары", "Услуги", "ЕГАИС", "Алкоголь",
    "Пиво разливное Россия", "Пиво импортное", "Пиво бутылочное", "Сидр", 
    "Водка", "Самогон", "Настойки", "Чача/Грапа", "Джин", "Виски/Бурбон", 
    "Текила", "Ром", "Коньяк/Бренди", "Аперитивы", "Ликеры и настойки", 
    "Вермуты", "Игристые вина", "Тихие белые вина", "Тихие розовые вина", 
    "Тихие красные вина", "Крепленые вина", "Б/а напитки", "Коктейли по контракту"
]

# --- ГРАНУЛЯРНЫЙ КАТЕГОРИЗАТОР (V20.0 - НОВЫЕ ИКОНКИ) ---
def detect_category_granular(name_input):
    name = str(name_input).strip().lower()
    
    # 1. ЕДА (КУХНЯ)
    food_keywords = ['бургер', 'суп', 'салат', 'фри', 'сыр', 'мясо', 'стейк', 'хлеб', 'соус', 'картофель', 'гренки', 'крылья', 'креветки', 'паста', 'сухарики', 'сэндвич', 'добавка', 'десерт', 'мороженое', 'чизкейк', 'начос', 'кесадилья']
    if any(w in name for w in food_keywords): return '🍔 Еда (Кухня)'

    # 2. ДОПЫ
    extra_keywords = ['сироп', 'доп.', 'сливки', 'молоко 50', 'лимон 20', 'лайм 20', 'мята 20', 'апельсин 20', 'мёд']
    if any(w in name for w in extra_keywords): return '🍬 Доп. ингредиенты'

    # 3. БЕЗАЛКОГОЛЬНОЕ (ДЕТАЛИЗАЦИЯ)
    
    # 3.1 Кофе
    if any(w in name for w in ['кофе', 'капучино', 'латте', 'эспрессо', 'американо', 'раф', 'флэт уайт', 'флэт-уайт']): return '☕ Кофе'
    
    # 3.2 Чай
    if any(w in name for w in ['чай', 'сенча', 'пуэр', 'эрл грей', 'ассам', 'улун', 'те гуань']): return '🍵 Чай'
    
    # 3.3 Милк/Фреш/Смузи
    if any(w in name for w in ['смузи', 'милк', 'шейк', 'фреш', 'fresh']): return '🍓 Милк/Фреш/Смузи'
    
    # 3.4 Коктейли Б/А (НОВАЯ ИКОНКА 🧉)
    if 'б/а' in name and any(w in name for w in ['мохито', 'пина', 'глинтвейн', 'коктейль']): return '🧉 Коктейль Б/А'
    if any(w in name for w in ['пино колада б/а', 'глинтвейн б/а']): return '🧉 Коктейль Б/А'

    # 3.5 Розлив Б/А (Домашнее)
    if any(w in name for w in ['морс', 'лимонад', 'напиток', 'компот']): 
        if not any(b in name for b in ['черноголовка', 'натахтари', 'стекло']):
            return '🚰 Розлив Б/А'

    # 3.6 Стекло/Банка Б/А
    if any(w in name for w in ['кола', 'cola', 'pepsi', 'тоник', 'tonic', 'red bull', 'ред булл', 'берн', 'адреналин', 'rich', 'рич', 'добрый', 'черноголовка', 'боржоми', 'bonaqua', 'вода', 'water', 'натахтари', 'чито', 'стекло', 'ж/б']): return '🥤 Стекло/Банка Б/А'

    # 4. АЛКОГОЛЬ (ДЕТАЛИЗАЦИЯ)

    # 4.1 Пиво и Сидр
    if 'сидр' in name or 'cider' in name or 'chester' in name: return '🍏 Сидр ШТ'
    
    beer_bottle_brands = ['corona', 'корона', 'clausthaler', 'клаусталер', 'бут', 'шт', '0.33', 'bda']
    if any(w in name for w in beer_bottle_brands) and ('пиво' in name or 'beer' in name or 'lager' in name or 'stout' in name or 'ale' in name): return '🍾 Пиво ШТ'
    
    beer_draft_keywords = ['пиво', 'beer', 'ale', 'ipa', 'lager', 'stout', 'светлое', 'темное', 'нефильтрованное', 'местное', 'шпатен', 'spaten', 'крушовице', 'гиннесс', 'прага', 'фирменное', '500', '300', '0.5']
    if any(w in name for w in beer_draft_keywords): return '🍺 Пиво Розлив'

    # 4.2 Виски
    whiskey_brands = ['виски', 'whiskey', 'whisky', 'jameson', 'джемесон', 'jack', 'jim beam', 'macallan', 'chivas', 'чивас', 'ballantine', 'балантайнс', 'поугс', 'pogues', 'proper', 'пропер', 'dewar', 'дюарс', 'red label', 'black label', 'bushmills']
    if any(w in name for w in whiskey_brands): return '🥃 Виски'

    # 4.3 Водка
    vodka_brands = ['водка', 'vodka', 'белуга', 'beluga', 'хаски', 'husky', 'онегин', 'onegin', 'finlandia', 'финляндия', 'абсолют', 'absolut', 'греy goose', 'чистые росы', 'нерпа', 'ортодокс', 'царская']
    if any(w in name for w in vodka_brands): return '💧 Водка'

    # 4.4 Ром
    rum_brands = ['ром', 'rum', 'bacardi', 'бакарди', 'morgan', 'морган', 'havana', 'гавана', 'barcelo', 'барсело', 'dead man', 'дэд мэн', 'brugal', 'бругал', 'zacapa']
    if any(w in name for w in rum_brands): return '🏴‍☠️ Ром'

    # 4.5 Текила
    tequila_brands = ['текила', 'tequila', 'olmeca', 'ольмека', 'espolon', 'эсполон', 'sauza', 'сауза', 'patron', 'патрон', 'don julio']
    if any(w in name for w in tequila_brands): return '🌵 Текила'

    # 4.6 Джин
    gin_brands = ['джин', 'gin', 'beefeater', 'бифитер', 'gordon', 'гордон', 'bombay', 'бомбей', 'barrister', 'барристер', 'baboon', 'бабун', 'hendrick', 'tanqueray']
    if any(w in name for w in gin_brands): return '🌲 Джин'

    # 4.7 Коньяк/Бренди
    cognac_brands = ['коньяк', 'cognac', 'бренди', 'brandy', 'арарат', 'ararat', 'ной', 'hennessy', 'хеннесси', 'courvoisier', 'курвуазье', 'martell', 'мартель', 'remy martin', 'торрес', 'torres', 'сараджишвили']
    if any(w in name for w in cognac_brands): return '🍇 Коньяк/Бренди'

    # 4.8 Ликеры и Настойки (НОВАЯ ИКОНКА 🍒)
    liqueur_brands = ['ликер', 'liqueur', 'настойка', 'нк ', 'егерь', 'jager', 'baileys', 'бейлиз', 'sambuca', 'самбука', 'absinthe', 'абсент', 'aperol', 'апероль', 'campari', 'кампари', 'becherovka', 'бехеровка', 'мартини', 'martini', 'чинзано', 'cinzano', 'чача']
    if any(w in name for w in liqueur_brands): return '🍒 Ликер/Настойка'

    # 5. ВИНО
    wine_keywords = ['вино', 'wine', 'брют', 'сек', 'сух', 'п/сл', 'просекко', 'prosecco', 'cava', 'кава', 'шампанское', 'рислинг', 'пино', 'мерло', 'шардоне', 'совиньон', 'кьянти', 'шираз', 'мальбек', 'каберне', 'ламбруско', 'асти', 'asti']
    if any(w in name for w in wine_keywords): return '🍷 Вино'

    # 6. КОКТЕЙЛИ
    cocktail_keywords = ['коктейль', 'шот', 'лонг', 'сэт', 'физ', 'негрони', 'сауэр', 'шприц', 'спритц', 'spritz', 'дайкири', 'маргарита', 'b-52', 'б-52', 'хиросима', 'облака', 'май тай', 'зомби', 'лонг айленд', 'пина колада', 'голубые гавайи']
    if any(w in name for w in cocktail_keywords): return '🍹 Коктейли'

    return '📦 Прочее'

# --- ПАРСИНГ ДАТЫ ---
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
            month_map = {'jan': 'января', 'feb': 'февраля', 'mar': 'марта', 'apr': 'апреля', 'may': 'мая', 'jun': 'июня', 'jul': 'июля', 'aug': 'августа', 'sep': 'сентября', 'oct': 'октября', 'nov': 'ноября', 'dec': 'декабря'}
            for eng, rus in month_map.items():
                if eng in filename.lower():
                     d_match = re.search(r'(\d{1,2})', filename)
                     if d_match:
                         current_year = datetime.now().year
                         report_date = datetime(current_year, RUS_MONTHS[rus], int(d_match.group(1)))
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

        col_name = df.columns[0]
        df = df.dropna(subset=[col_name])
        df = df[~df[col_name].astype(str).str.strip().isin(IGNORE_NAMES)]
        df = df[~df[col_name].astype(str).str.contains("Итого", case=False)]
        
        cols_to_num = ['Количество', 'Себестоимость', 'Выручка с НДС']
        for col in cols_to_num:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df['Unit_Cost'] = np.where(df['Количество'] != 0, df['Себестоимость'] / df['Количество'], 0)
        df['Фудкост'] = np.where(df['Выручка с НДС'] > 0, (df['Себестоимость'] / df['Выручка с НДС'] * 100), 0)
        df['Дата_Отчета'] = report_date
        df = df.rename(columns={col_name: 'Блюдо'})
        
        # ПРИМЕНЯЕМ ГРАНУЛЯРНЫЙ КАТЕГОРИЗАТОР
        df['Категория'] = df['Блюдо'].apply(detect_category_granular)

        return df
    except Exception:
        return None

@st.cache_data(ttl=3600, show_spinner="Скачиваем данные с Яндекс.Диска...")
def load_all_from_yandex(folder_path):
    token = st.secrets.get("YANDEX_TOKEN")
    if not token: return None
    headers = {'Authorization': f'OAuth {token}'}
    api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
    params = {'path': folder_path, 'limit': 2000}
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
            except: continue
        return data_frames
    except: return []

# --- ИНТЕРФЕЙС ЗАГРУЗКИ ---
st.sidebar.header("📂 1. Источник данных")
source_mode = st.sidebar.radio("Откуда берем отчеты?", ["Яндекс.Диск", "Ручная загрузка"])

if st.sidebar.button("🗑 Сбросить все данные"):
    st.cache_data.clear()
    st.session_state.df_full = None
    st.rerun()

if source_mode == "Ручная загрузка":
    uploaded_files = st.sidebar.file_uploader("Загрузить отчеты (CSV/Excel)", accept_multiple_files=True)
    if uploaded_files:
        temp_data = []
        for f in uploaded_files:
            df = process_single_file(f, f.name)
            if df is not None: temp_data.append(df)
        if temp_data:
            st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')
elif source_mode == "Яндекс.Диск":
    yandex_path = st.sidebar.text_input("Папка на Диске:", "Отчеты_Ресторан")
    if st.sidebar.button("🔄 Скачать отчеты"):
        if not st.secrets.get("YANDEX_TOKEN"):
             st.error("⚠️ Нет токена в Secrets!")
        else:
            temp_data = load_all_from_yandex(yandex_path)
            if temp_data:
                st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')
                st.success(f"Загружено {len(temp_data)} отчетов!")
            else:
                st.warning("Файлов не найдено.")

# --- МЕНЕДЖЕР КАТЕГОРИЙ (РУЧНОЙ) ---
st.sidebar.write("---")
st.sidebar.header("🗂️ Ручная правка")
st.sidebar.info("Если автомат ошибся, загрузи исправленный список (Блюдо, Категория).")
category_file = st.sidebar.file_uploader("Файл справочника", type=['csv', 'xlsx'])

if st.session_state.df_full is not None and category_file is not None:
    try:
        if category_file.name.endswith('.csv'):
            cat_df = pd.read_csv(category_file)
        else:
            cat_df = pd.read_excel(category_file)
        col_item = next((c for c in cat_df.columns if 'блюдо' in c.lower() or 'item' in c.lower()), None)
        col_cat = next((c for c in cat_df.columns if 'категория' in c.lower() or 'category' in c.lower()), None)
        if col_item and col_cat:
            mapping = dict(zip(cat_df[col_item], cat_df[col_cat]))
            st.session_state.df_full['Категория'] = st.session_state.df_full['Блюдо'].map(mapping).fillna(st.session_state.df_full['Категория'])
            st.sidebar.success(f"✅ Справочник применен!")
    except: pass

# --- АНАЛИТИКА ---
if st.session_state.df_full is not None:
    df_full = st.session_state.df_full
    
    with st.sidebar:
        st.write("---")
        csv = df_full.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Скачать базу (CSV)", csv, f"Analytics_{datetime.now().date()}.csv", "text/csv")

    dates_list = sorted(df_full['Дата_Отчета'].unique(), reverse=True)
    date_options = ["📅 ВСЕ ВРЕМЯ (Сводный)"] + [d.strftime('%d.%m.%Y') for d in dates_list]
    
    st.write("---")
    col_sel1, col_sel2 = st.columns([1, 4])
    selected_option = col_sel1.selectbox("Период:", date_options)
    
    if "ВСЕ ВРЕМЯ" in selected_option:
        target_date = df_full['Дата_Отчета'].max()
        df_view = df_full 
    else:
        target_date = datetime.strptime(selected_option, '%d.%m.%Y')
        df_view = df_full[df_full['Дата_Отчета'] == target_date]

    # KPI
    total_rev = df_view['Выручка с НДС'].sum()
    total_cost = df_view['Себестоимость'].sum()
    avg_fc = (total_cost / total_rev * 100) if total_rev > 0 else 0
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("💰 Выручка", f"{total_rev:,.0f} ₽")
    kpi2.metric("📉 Фуд-кост", f"{avg_fc:.1f} %")
    kpi3.metric("💳 Маржа", f"{(total_rev - total_cost):,.0f} ₽")
    kpi4.metric("🧾 Позиций", len(df_view))

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔥 Инфляция и Потери", "🍰 Меню и Косты", "⭐ Матрица (ABC)", "🗓 Дни недели", "📦 План Закупок"])

    # --- 1. ИНФЛЯЦИЯ ---
    with tab1:
        st.subheader(f"🔥 Инфляционный Трекер (по состоянию на {target_date.strftime('%d.%m.%Y')})")
        
        df_inflation_scope = df_full[df_full['Дата_Отчета'] <= target_date]
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
                st.write("### 📉 Топ-30 Потерь")
                if not df_inf.empty:
                    df_up = df_inf[df_inf['Рост %'] > 0].sort_values('Эффект (₽)', ascending=False).head(30)
                    st.dataframe(df_up[['Товар', 'Рост %', 'Эффект (₽)']].style.format({'Рост %': "+{:.1f} %", 'Эффект (₽)': "-{:,.0f} ₽"}).background_gradient(subset=['Эффект (₽)'], cmap='Reds'), use_container_width=True)
            with col_down:
                st.write("### 📈 Топ-30 Экономии")
                if not df_inf.empty:
                    df_down = df_inf[df_inf['Рост %'] < 0].sort_values('Эффект (₽)', ascending=True).head(30)
                    st.dataframe(df_down[['Товар', 'Рост %', 'Эффект (₽)']].style.format({'Рост %': "{:.1f} %", 'Эффект (₽)': "+{:,.0f} ₽"}).background_gradient(subset=['Эффект (₽)'], cmap='Greens_r'), use_container_width=True)
        else:
            st.success("Цены стабильны.")

    # --- 2. МЕНЮ И КОСТЫ ---
    with tab2:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Структура выручки")
            df_cat = df_view.groupby('Категория')['Выручка с НДС'].sum().reset_index()
            fig_pie = px.pie(df_cat, values='Выручка с НДС', names='Категория', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with c2:
            st.subheader("📊 Детальный анализ Фуд-коста")
            df_menu = df_view.groupby('Блюдо').agg({'Выручка с НДС': 'sum', 'Себестоимость': 'sum', 'Количество': 'sum'}).reset_index()
            df_menu['Фудкост %'] = np.where(df_menu['Выручка с НДС']>0, df_menu['Себестоимость']/df_menu['Выручка с НДС']*100, 0)
            df_menu = df_menu.sort_values('Выручка с НДС', ascending=False).head(50)
            st.dataframe(df_menu[['Блюдо', 'Выручка с НДС', 'Фудкост %']].style.format({'Выручка с НДС': "{:,.0f} ₽", 'Фудкост %': "{:.1f} %"}).background_gradient(subset=['Фудкост %'], cmap='Reds', vmin=20, vmax=60), use_container_width=True, height=400)

        st.write("---")
        st.subheader("🕵️‍♀️ Аудит категорий (Что попало в 'Прочее')")
        uncategorized = df_view[df_view['Категория'].str.contains('Прочее', case=False)]['Блюдо'].unique()
        if len(uncategorized) > 0:
            st.warning(f"Есть {len(uncategorized)} нераспознанных блюд.")
            st.dataframe(pd.DataFrame(uncategorized, columns=['Нераспознанные блюда']), use_container_width=True)
        else:
            st.success("Все блюда распределены!")

    # --- 3. ABC МАТРИЦА ---
    with tab3:
        st.subheader("⭐ Матрица Меню (ABC)")
        col_L1, col_L2, col_L3, col_L4 = st.columns(4)
        col_L1.info("⭐ **Звезды**\n\nВысокая маржа, Популярные.")
        col_L2.warning("🐎 **Лошадки**\n\nНизкая маржа, Популярные.")
        col_L3.success("❓ **Загадки**\n\nВысокая маржа, Мало продаж.")
        col_L4.error("🐶 **Собаки**\n\nНизкая маржа, Мало продаж.")

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
        fig_abc = px.scatter(abc_df, x="Количество", y="Unit_Margin", color="Класс", hover_name="Блюдо", size="Выручка с НДС", color_discrete_map={"⭐ Звезда": "gold", "🐎 Лошадка": "blue", "❓ Загадка": "green", "🐶 Собака": "red"}, log_x=True)
        fig_abc.update_traces(hovertemplate='<b>%{hovertext}</b><br>Продажи: %{x} шт<br>Маржа с блюда: %{y:.0f} ₽')
        fig_abc.add_vline(x=avg_qty, line_dash="dash", line_color="gray")
        fig_abc.add_hline(y=avg_margin, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_abc, use_container_width=True)

    # --- 4. ДНИ НЕДЕЛИ ---
    with tab4:
        st.subheader("🗓 Дни недели")
        if len(dates_list) > 1:
            df_full['ДеньНедели'] = df_full['Дата_Отчета'].dt.day_name()
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            days_rus = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
            dow_stats = df_full.groupby(['Дата_Отчета', 'ДеньНедели'])['Выручка с НДС'].sum().reset_index().groupby('ДеньНедели')['Выручка с НДС'].mean().reindex(days_order).reset_index()
            dow_stats['ДеньРус'] = days_rus
            fig_dow = px.bar(dow_stats, x='ДеньРус', y='Выручка с НДС', color='Выручка с НДС')
            fig_dow.update_traces(texttemplate='%{y:,.0f} ₽', textposition='auto')
            st.plotly_chart(fig_dow, use_container_width=True)
        else:
            st.warning("Мало данных.")

    # --- 5. ПЛАН ЗАКУПОК ---
    with tab5:
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
        st.dataframe(plan_df[['Блюдо', 'Unit_Cost', 'Need_Qty', 'Budget']].style.format({'Unit_Cost': "{:.1f} ₽", 'Need_Qty': "{:.1f}", 'Budget': "{:,.0f} ₽"}).background_gradient(subset=['Budget'], cmap='Greens'), use_container_width=True)

else:
    st.info("👈 Загрузите данные.")
