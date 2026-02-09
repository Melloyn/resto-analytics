import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta

from processing import get_macro_category, process_single_file

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="RestoAnalytics: Место", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Аналитика: Бар МЕСТО")

# --- ИНИЦИАЛИЗАЦИЯ ПАМЯТИ ---
if 'df_full' not in st.session_state:
    st.session_state.df_full = None


@st.cache_data(ttl=3600, show_spinner="Скачиваем данные с Яндекс.Диска...")
def load_all_from_yandex(folder_path):
    token = st.secrets.get("YANDEX_TOKEN")
    if not token: return None
    headers = {'Authorization': f'OAuth {token}'}
    api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
    params = {'path': folder_path, 'limit': 2000}
    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=20)
        if response.status_code != 200: return []
        items = response.json().get('_embedded', {}).get('items', [])
        files = [i for i in items if i['type'] == 'file']
        data_frames = []
        for item in files:
            try:
                file_resp = requests.get(item['file'], headers=headers, timeout=20)
                df, error, warnings = process_single_file(BytesIO(file_resp.content), filename=item['name'])
                if error:
                    st.warning(error)
                else:
                    for warning in warnings:
                        st.warning(warning)
                if df is not None:
                    data_frames.append(df)
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
            df, error, warnings = process_single_file(f, f.name)
            if error:
                st.warning(error)
            else:
                for warning in warnings:
                    st.warning(warning)
            if df is not None:
                temp_data.append(df)
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
    # ЛЕЧЕНИЕ ДАННЫХ В ПАМЯТИ (Если вдруг нет колонки)
    if 'Поставщик' not in st.session_state.df_full.columns:
        st.session_state.df_full['Поставщик'] = 'Не указан'

    df_full = st.session_state.df_full.copy()
    df_full['Макро_Категория'] = df_full['Категория'].apply(get_macro_category)
    
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

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔥 Инфляция", "📉 Динамика и Поставщики", "🍰 Меню и Косты", "⭐ Матрица (ABC)", "🗓 Дни недели", "📦 План Закупок"])

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
                st.write("### 🔺 Топ-30: Цена выросла (Убыток)")
                if not df_inf.empty:
                    df_up = df_inf[df_inf['Рост %'] > 0].sort_values('Эффект (₽)', ascending=False).head(30)
                    st.dataframe(df_up[['Товар', 'Рост %', 'Эффект (₽)']].style.format({'Рост %': "+{:.1f} %", 'Эффект (₽)': "-{:,.0f} ₽"}).background_gradient(subset=['Эффект (₽)'], cmap='Reds'), use_container_width=True)
            with col_down:
                st.write("### 🔻 Топ-30: Цена упала (Экономия)")
                if not df_inf.empty:
                    df_down = df_inf[df_inf['Рост %'] < 0].sort_values('Эффект (₽)', ascending=True).head(30)
                    st.dataframe(df_down[['Товар', 'Рост %', 'Эффект (₽)']].style.format({'Рост %': "{:.1f} %", 'Эффект (₽)': "+{:,.0f} ₽"}).background_gradient(subset=['Эффект (₽)'], cmap='Greens_r'), use_container_width=True)
        else:
            st.success("Цены стабильны.")

    # --- 2. ДИНАМИКА И ПОСТАВЩИКИ ---
    with tab2:
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
                st.plotly_chart(fig_trend, use_container_width=True)
                
                # БЕЗОПАСНЫЙ ВЫВОД ТАБЛИЦЫ
                cols_to_show = ['Дата_Отчета', 'Unit_Cost']
                if 'Поставщик' in item_data.columns:
                    cols_to_show.append('Поставщик')
                
                st.dataframe(item_data[cols_to_show].style.format({'Unit_Cost': '{:.2f} ₽', 'Дата_Отчета': '{:%d.%m.%Y}'}), use_container_width=True)
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
                    st.plotly_chart(fig_sup, use_container_width=True)
                else:
                    st.info("Данные по поставщикам не найдены.")
            else:
                st.info("В загруженных файлах нет колонки 'Поставщик'.")

    # --- 3. МЕНЮ И КОСТЫ ---
    with tab3:
        view_mode = st.radio("Детализация категорий:", ["🔍 Укрупненно (Макро-группы)", "🔬 Детально (Микро-категории)"], horizontal=True)
        target_cat = 'Макро_Категория' if 'Макро' in view_mode else 'Категория'

        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Структура выручки")
            df_cat = df_view.groupby(target_cat)['Выручка с НДС'].sum().reset_index()
            fig_pie = px.pie(df_cat, values='Выручка с НДС', names=target_cat, hole=0.4)
            fig_pie.update_traces(hovertemplate='%{label}: %{value:,.0f} ₽ (%{percent})')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with c2:
            st.subheader("📊 Детальный анализ Фуд-коста")
            df_menu = df_view.groupby(['Блюдо', target_cat]).agg({'Выручка с НДС': 'sum', 'Себестоимость': 'sum', 'Количество': 'sum'}).reset_index()
            df_menu['Фудкост %'] = np.where(df_menu['Выручка с НДС']>0, df_menu['Себестоимость']/df_menu['Выручка с НДС']*100, 0)
            df_menu = df_menu.sort_values('Выручка с НДС', ascending=False).head(50)
            df_menu = df_menu.rename(columns={target_cat: 'Категория'})
            st.dataframe(df_menu[['Блюдо', 'Категория', 'Выручка с НДС', 'Фудкост %']].style.format({'Выручка с НДС': "{:,.0f} ₽", 'Фудкост %': "{:.1f} %"}).background_gradient(subset=['Фудкост %'], cmap='Reds', vmin=20, vmax=60), use_container_width=True, height=400)

        st.write("---")
        st.subheader("🕵️‍♀️ Аудит категорий (Что попало в 'Прочее')")
        uncategorized = df_view[df_view['Категория'].str.contains('Прочее', case=False)]['Блюдо'].unique()
        if len(uncategorized) > 0:
            st.warning(f"Есть {len(uncategorized)} нераспознанных блюд.")
            st.dataframe(pd.DataFrame(uncategorized, columns=['Нераспознанные блюда']), use_container_width=True)
        else:
            st.success("Все блюда распределены!")

    # --- 4. ABC МАТРИЦА ---
    with tab4:
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
        st.plotly_chart(fig_abc, use_container_width=True)

    # --- 5. ДНИ НЕДЕЛИ ---
    with tab5:
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

    # --- 6. ПЛАН ЗАКУПОК ---
    with tab6:
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
