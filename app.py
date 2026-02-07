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

# --- УМНЫЙ КАТЕГОРИЗАТОР ---
def detect_category(name_input):
    name = str(name_input).lower()
    
    # ПИВО И СИДР
    beer_brands = [
        'крушовице', 'мейзон', 'арне', 'баден', 'блэк шип', 'радебергер', 'вудбридж', 
        'либенвайс', 'бакалар', 'бланш де намю', 'эстрелла', 'бургунь', 'штигль', 
        'франц', 'фердинанд', 'кастил руж', 'прага', 'штейнброй', 'айингер', 
        'эрдингер', 'аркоброй', 'шпатен', 'пауланер', 'будвайзер', 'вайценфельд', 
        'гиннесс', 'натахтари', 'арго', 'честерс', 'сидр', 'василеостровская'
    ]
    
    # ВИНО
    wine_brands = [
        'просекко', 'каза дефра', 'ламбруско', 'балаклава', 'нуволе', 'шато тамань', 
        'тет де шеваль', 'чинзано асти', 'чинзано просекко', 'рислинг', 'авторское', 
        'абрау', 'гаэтано', 'фрескелло', 'трапиче', 'селлар', 'ханс баер', 'альма романа', 
        'шардоне', 'гато негро', 'ле гран нуар', 'лакки', 'тини', 'терре аллегре', 
        'пфефферер', 'маре', 'халео', 'пти шабли', 'санте риве', 'бесини', 'шилдис', 
        'мамико', 'ркацители', 'трезвая голова', 'бухта омега', 'ведерниковъ', 
        'телави', 'гринлайф', 'кампело', 'каффа', 'домашнее', 'сокровище тифлиса', 
        'твиши', 'цинандали', 'антико', 'пино гриджо', 'кьянти', 'бруни', 'примасоле', 
        'ла ситель', 'кампо делия', 'сигло', 'киндзмараули', 'саперави', 'ежевичное', 
        'тамариани', 'хванчкара', 'мукузани', 'пинотаж', 'херес', 'тио тото'
    ]
    
    # КРЕПКОЕ
    strong_brands = [
        'хаски', 'белая берёзка', 'сибирский экспресс', 'чисты росы', 'белуга', 
        'пять озёр', 'мамонт', 'онегин', 'самоваръ', 'чача', 'асканели', 'грин бабун', 
        'broom', 'мэйфэйр', 'целовальник', 'беркшир', 'уитли', 'сэр эдвардс', 'сеа вич', 
        'траблмейкер', 'джемесон', 'чивас', 'баллантайнс', 'гленливет', 'макаллан', 
        'тейстил', 'гериозе', 'блэк рэм', 'вильям лоусон', 'харт бразерс', 'поугс', 
        'бэнкхолл', 'крэбби', 'абер фоллс', 'эль бандидо', 'эсполон', 'дон алехандро', 
        'барсело', 'калентер', 'капитанский', 'дэд мэн', 'бисквит', 'торрес', 
        'сараджишвили', 'камю', 'мартиньяк', 'апероль', 'кампари', 'лигаре', 'соджу', 
        'тундра', 'самбука', 'абсент', 'лимончелло', 'fruko', 'ламоника', 'бутурлин', 
        'ягермайстер', 'чинзано бьянко', 'чинзано россо', 'чинзано экстра'
    ]
    
    # КОКТЕЙЛИ
    cocktail_brands = [
        'tropical sour', 'pineapple spritz', 'passion star', 'берк-тоник', 
        'watermelon gin', 'хаскиринья'
    ]
    
    # БЕЗАЛКОГОЛЬНОЕ
    non_alc_brands = [
        'сок рич', 'морс', 'сок добрый', 'рич кола', 'добрый апельсин', 'добрый лимон', 
        'добрый кола', 'рич тоник', 'бона аква', 'берн', 'боржоми', 'саирме', 'ред булл', 
        'лимонад', 'чито-грито', 'черноголовка', 'вода 4 воды'
    ]

    # ЕДА (Пока по ключевым словам)
    food_keywords = ['бургер', 'суп', 'салат', 'фри', 'сыр', 'мясо', 'стейк', 'хлеб', 'соус', 'картофель', 'гренки', 'крылья', 'креветки', 'паста', 'сухарики', 'сэндвич', 'добавка', 'десерт', 'мороженое', 'чизкейк', 'начос', 'кесадилья']

    # --- ЛОГИКА ---
    if any(b in name for b in beer_brands): return '🍺 Пиво/Сидр'
    if any(b in name for b in wine_brands): return '🍷 Вино'
    if any(b in name for b in strong_brands): return '🥃 Крепкое'
    if any(b in name for b in cocktail_brands): return '🍹 Коктейли'
    if any(b in name for b in non_alc_brands): return '☕ Безалкогольное'
    
    # Резервные слова
    if any(w in name for w in ['пиво', 'beer', 'ale', 'ipa', 'lager', 'stout']): return '🍺 Пиво/Сидр'
    if any(w in name for w in ['вино', 'wine', 'брют', 'сек', 'сух']): return '🍷 Вино'
    if any(w in name for w in ['водка', 'виски', 'ром', 'джин', 'текила', 'коньяк']): return '🥃 Крепкое'
    if any(w in name for w in ['коктейль', 'шот', 'long']): return '🍹 Коктейли'
    if any(w in name for w in ['вода', 'сок', 'чай', 'кофе', 'cola']): return '☕ Безалкогольное'
    
    if any(w in name for w in food_keywords): return '🍔 Еда (Кухня)'

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
        df['Категория'] = df['Блюдо'].apply(detect_category)
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

# --- ИНТЕРФЕЙС ---
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

if st.session_state.df_full is not None:
    df_full = st.session_state.df_full
    
    # Экспорт
    with st.sidebar:
        st.write("---")
        csv = df_full.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Скачать (CSV)", csv, f"Analytics_{datetime.now().date()}.csv", "text/csv")

    # Фильтр дат
    dates_list = sorted(df_full['Дата_Отчета'].unique(), reverse=True)
    date_options = ["📅 ВСЕ ВРЕМЯ (Сводный)"] + [d.strftime('%d.%m.%Y') for d in dates_list]
    
    st.write("---")
    col_sel1, col_sel2 = st.columns([1, 4])
    selected_option = col_sel1.selectbox("Период:", date_options)
    
    # ЛОГИКА ФИЛЬТРАЦИИ
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
        st.caption("Расчет потерь и экономии на основе изменения закупочных цен.")
        
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
                    
                    if financial_impact > 0:
                        total_gross_loss += financial_impact
                    else:
                        total_gross_save += abs(financial_impact)

                    if abs(diff_pct) > 1:
                        inflation_data.append({
                            'Товар': item,
                            'Старая цена': first_price,
                            'Новая цена': last_price,
                            'Рост %': diff_pct,
                            'Эффект (₽)': financial_impact
                        })
        
        net_result = total_gross_loss - total_gross_save
        
        inf1, inf2, inf3 = st.columns(3)
        inf1.metric("🔴 Потери (Инфляция)", f"-{total_gross_loss:,.0f} ₽", help="Сумма денег, потерянная из-за роста цен закупки.")
        inf2.metric("🟢 Экономия (Скидки)", f"+{total_gross_save:,.0f} ₽", help="Сумма денег, сэкономленная на снижении цен закупки.")
        inf3.metric("🏁 Чистый Итог", f"-{net_result:,.0f} ₽" if net_result > 0 else f"+{abs(net_result):,.0f} ₽", 
                   delta_color="inverse")
        
        st.write("---")

        if inflation_data:
            df_inf = pd.DataFrame(inflation_data)
            
            df_up = df_inf[df_inf['Рост %'] > 0].sort_values('Эффект (₽)', ascending=False).head(30)
            df_down = df_inf[df_inf['Рост %'] < 0].sort_values('Эффект (₽)', ascending=True).head(30)

            col_up, col_down = st.columns(2)

            with col_up:
                st.write("### 📉 Топ-30 Потерь (Цена выросла)")
                if not df_up.empty:
                    st.dataframe(df_up[['Товар', 'Рост %', 'Эффект (₽)']].style.format({'Рост %': "+{:.1f} %", 'Эффект (₽)': "-{:,.0f} ₽"}).background_gradient(subset=['Эффект (₽)'], cmap='Reds'), use_container_width=True)
                else:
                    st.success("Нет потерь.")

            with col_down:
                st.write("### 📈 Топ-30 Экономии (Цена упала)")
                if not df_down.empty:
                    st.dataframe(df_down[['Товар', 'Рост %', 'Эффект (₽)']].style.format({'Рост %': "{:.1f} %", 'Эффект (₽)': "+{:,.0f} ₽"}).background_gradient(subset=['Эффект (₽)'], cmap='Greens_r'), use_container_width=True)
                else:
                    st.info("Нет экономии.")
        else:
            st.success("Цены стабильны.")

    # --- 2. МЕНЮ И КОСТЫ (С ДЕТЕКТИВОМ) ---
    with tab2:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Структура выручки")
            df_cat = df_view.groupby('Категория')['Выручка с НДС'].sum().reset_index()
            fig_pie = px.pie(df_cat, values='Выручка с НДС', names='Категория', hole=0.4)
            fig_pie.update_traces(hovertemplate='%{label}: %{value:,.0f} ₽ (%{percent})')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with c2:
            st.subheader("📊 Детальный анализ Фуд-коста")
            df_menu = df_view.groupby('Блюдо').agg({'Выручка с НДС': 'sum', 'Себестоимость': 'sum', 'Количество': 'sum'}).reset_index()
            df_menu['Фудкост %'] = np.where(df_menu['Выручка с НДС']>0, df_menu['Себестоимость']/df_menu['Выручка с НДС']*100, 0)
            df_menu = df_menu.sort_values('Выручка с НДС', ascending=False).head(50)
            st.dataframe(df_menu[['Блюдо', 'Выручка с НДС', 'Фудкост %']].style.format({'Выручка с НДС': "{:,.0f} ₽", 'Фудкост %': "{:.1f} %"}).background_gradient(subset=['Фудкост %'], cmap='Reds', vmin=20, vmax=60), use_container_width=True, height=400)

        # === ДЕТЕКТИВ КАТЕГОРИЙ ===
        st.write("---")
        st.subheader("🕵️‍♀️ Аудит категорий (Что попало в 'Прочее')")
        # Берем данные из ПОЛНОГО df, чтобы найти все возможные ошибки за все время
        uncategorized = df_full[df_full['Категория'] == '📦 Прочее']['Блюдо'].unique()
        
        if len(uncategorized) > 0:
            st.warning(f"Найдено {len(uncategorized)} позиций, которые я не смог распознать. Скопируй таблицу ниже и пришли разработчику.")
            st.dataframe(pd.DataFrame(uncategorized, columns=['Нераспознанные блюда']), use_container_width=True)
        else:
            st.success("Отлично! Все блюда успешно распределены по категориям.")

    # --- 3. ABC МАТРИЦА ---
    with tab3:
        st.subheader("⭐ Матрица Меню (ABC)")
        col_L1, col_L2, col_L3, col_L4 = st.columns(4)
        col_L1.info("⭐ **Звезды**\n\nВысокая маржа, Популярные. \n**Стратегия:** Беречь!")
        col_L2.warning("🐎 **Лошадки**\n\nНизкая маржа, Популярные. \n**Стратегия:** Чуть поднять цену.")
        col_L3.success("❓ **Загадки**\n\nВысокая маржа, Мало продаж. \n**Стратегия:** Рекламировать.")
        col_L4.error("🐶 **Собаки**\n\nНизкая маржа, Мало продаж. \n**Стратегия:** Убрать.")

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
            fig_dow.update_layout(yaxis_tickformat = ',.0f')
            st.plotly_chart(fig_dow, use_container_width=True)
        else:
            st.warning("Мало данных.")

    # --- 5. ПЛАН ЗАКУПОК ---
    with tab5:
        st.subheader("📦 Калькулятор Закупки (на основе статистики)")
        st.info("Прогноз строится на средних продажах за последние 30 дней. Бюджет считается по последней цене закупки.")
        
        c_set1, c_set2 = st.columns(2)
        days_to_buy = c_set1.slider("📅 На сколько дней закупаем?", min_value=1, max_value=14, value=3)
        safety_stock = c_set2.slider("🛡 Страховой запас (%)", min_value=0, max_value=50, value=10)
        
        last_30_days = df_full['Дата_Отчета'].max() - timedelta(days=30)
        df_recent = df_full[df_full['Дата_Отчета'] >= last_30_days]
        
        daily_sales = df_recent.groupby('Блюдо')['Количество'].sum().reset_index()
        daily_sales['Avg_Daily_Qty'] = daily_sales['Количество'] / 30
        
        last_prices = df_full.sort_values('Дата_Отчета').groupby('Блюдо')['Unit_Cost'].last().reset_index()
        plan_df = pd.merge(daily_sales[['Блюдо', 'Avg_Daily_Qty']], last_prices, on='Блюдо')
        
        plan_df['Need_Qty'] = plan_df['Avg_Daily_Qty'] * days_to_buy * (1 + safety_stock/100)
        plan_df['Budget'] = plan_df['Need_Qty'] * plan_df['Unit_Cost']
        plan_df = plan_df[plan_df['Need_Qty'] > 0.5].sort_values('Budget', ascending=False)
        
        total_budget = plan_df['Budget'].sum()
        st.metric(label=f"💰 Бюджет на {days_to_buy} дн.", value=f"{total_budget:,.0f} ₽")
        
        st.dataframe(plan_df[['Блюдо', 'Unit_Cost', 'Need_Qty', 'Budget']].style.format({'Unit_Cost': "{:.1f} ₽", 'Need_Qty': "{:.1f} ед.", 'Budget': "{:,.0f} ₽"}).background_gradient(subset=['Budget'], cmap='Greens'), use_container_width=True)

else:
    st.info("👈 Загрузите данные.")
