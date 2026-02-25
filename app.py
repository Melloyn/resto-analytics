import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os
import telegram_utils

from views.reports import (
    kpi_view, inflation_view, export_view,
    menu_view, abc_view, simulator_view,
    weekday_view, procurement_view
)
from services import data_loader, analytics_service, category_service
import auth
import ui
from utils import session_manager
from use_cases import auth_flow, bootstrap
from views import admin_view, login_view
from datetime import datetime, timedelta

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="RestoAnalytics: Место", layout="wide", initial_sidebar_state="expanded")

# --- СТИЛИ И ЭФФЕКТЫ ---
ui.setup_style()
ui.setup_parallax()

# --- STARTUP ORCHESTRATION ---
startup_result = bootstrap.run_startup()
if startup_result.status == "STOP":
    st.stop()

# --- ВХОД / АВТОРИЗАЦИЯ ---
# 1. Orchestration: init session -> restore -> validate
auth_result = auth_flow.ensure_authenticated_session()

# 2. Если все еще не вошли -> Показываем логин
if auth_result.status == "STOP":
    login_view.render_auth_screen()
    st.stop()

# === ГЛАВНЫЙ ИНТЕРФЕЙС ===
if st.session_state.is_admin and st.session_state.admin_fullscreen:
    st.title("⚙️ Администрирование")
    if st.button("← Вернуться к аналитике", type="secondary"):
        st.session_state.admin_fullscreen = False
        st.session_state.admin_fullscreen_tab = None
        st.rerun()
    admin_view.render_admin_panel(None, default_tab=st.session_state.admin_fullscreen_tab)
    st.stop()

st.title(f"📊 Аналитика: {st.session_state.auth_user['full_name']}")

# --- VIEW CACHING HELPER ---
def get_view_cached(key, compute_func):
    full_key = (key, st.session_state.df_version, st.session_state.categories_applied_sig)
    if full_key in st.session_state.view_cache:
        return st.session_state.view_cache[full_key]
    val = compute_func()
    st.session_state.view_cache[full_key] = val
    return val

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/17929/17929252.png", width=70)
    
    if st.button("Выйти", key="logout_btn", type="secondary"):
        session_manager.logout()

    st.divider()

    # --- ADMIN AREA ---
    if st.session_state.is_admin:
        with st.expander("⚙️ Администрирование", expanded=False):
            if st.button("🖥️ Открыть в центре", use_container_width=True):
                st.session_state.admin_fullscreen = True
                st.session_state.admin_fullscreen_tab = None
                st.rerun()
            if st.button("📦 Прочее в центре", use_container_width=True):
                st.session_state.admin_fullscreen = True
                st.session_state.admin_fullscreen_tab = "misc"
                st.rerun()
            if not st.session_state.admin_fullscreen:
                admin_view.render_admin_panel(None)
        st.divider()

    # --- DATA LOADING ---
    tg_token = (
        auth.get_secret("TG_BOT_TOKEN")
        or auth.get_secret("TELEGRAM_TOKEN")
        or os.getenv("TG_BOT_TOKEN")
        or os.getenv("TELEGRAM_TOKEN")
    )
    tg_chat = (
        auth.get_secret("TG_CHAT_ID")
        or auth.get_secret("TELEGRAM_CHAT_ID")
        or os.getenv("TG_CHAT_ID")
        or os.getenv("TELEGRAM_CHAT_ID")
    )

    with st.expander("📂 Источник данных", expanded=False):
        # Yandex Path Config
        if st.session_state.edit_yandex_path:
             new_path = st.text_input("Путь на Яндекс.Диске", value=st.session_state.yandex_path)
             if st.button("Сохранить"):
                 st.session_state.yandex_path = new_path
                 st.session_state.edit_yandex_path = False
                 st.rerun()
        else:
            c_path1, c_path2 = st.columns([5, 1])
            c_path1.caption(f"📁 {st.session_state.yandex_path}")
            if c_path2.button("✏️", help="Изменить папку"):
                st.session_state.edit_yandex_path = True
                st.rerun()

        source_type = st.radio("Откуда берем?", ["☁️ Яндекс.Диск", "📂 Локальная папка"])

        if source_type == "☁️ Яндекс.Диск":
            yd_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
            if not yd_token:
                st.error("Нет токена Yandex Disk!")
            else:
                if st.button("🔄 Скачать и Обновить", type="primary", use_container_width=True):
                    ui.show_loading_overlay("Связываюсь с облаком...")
                    success, msg = data_loader.download_and_process_yandex(yd_token, st.session_state.yandex_path)
                    if success:
                        st.success("Данные обновлены!")
                        st.session_state.dropped_stats = data_loader.get_last_sync_meta().get(
                            "dropped_stats",
                            {"count": 0, "cost": 0.0, "items": []},
                        )
                        st.session_state.df_full = None
                        st.session_state.df_version += 1
                        st.rerun()
                    else:
                        st.error(msg)

        elif source_type == "📂 Локальная папка":
            if st.button("🔄 Загрузить из кэша"):
                 st.session_state.df_full = None
                 st.rerun()

    # --- AUTO-LOAD ---
    if st.session_state.df_full is None:
        if os.path.exists(data_loader.CACHE_FILE):
             try:
                 meta_ok = False
                 if os.path.exists(data_loader.SCHEMA_META_FILE):
                     try:
                         import json
                         with open(data_loader.SCHEMA_META_FILE, "r", encoding="utf-8") as f:
                             meta = json.load(f)
                         meta_ok = meta.get("schema_version") == data_loader.SCHEMA_VERSION
                     except Exception:
                         meta_ok = False
                 if not meta_ok:
                     st.warning("Кэш устарел. Нажмите «Скачать и обновить».")
                 else:
                     placeholder = st.empty()
                     with placeholder.container():
                         st.markdown("### Загрузка аналитики из кэша...")
                         ui.render_skeleton_kpis()
                         st.markdown("<br>", unsafe_allow_html=True)
                         ui.render_skeleton_chart()
                         import time; time.sleep(0.05) # Force UI flush
                     df = pd.read_parquet(data_loader.CACHE_FILE)
                     # Always re-apply categories from current mapping,
                     # so category edits survive app/server restarts.
                     df = category_service.apply_categories(df)
                     st.session_state.df_full = df
                     placeholder.empty()
             except Exception as e:
                 st.error(f"Ошибка чтения кэша: {e}")
    
    # --- FILTERS ---
    if st.session_state.df_full is not None:
        with st.expander("🗓️ Фильтры периода", expanded=False):
            df_full = st.session_state.df_full.copy()
            
            # 1. Venue Filter
            venue_col = "Точка" if "Точка" in df_full.columns else ("Venue" if "Venue" in df_full.columns else None)
            if venue_col:
                venues = sorted(df_full[venue_col].dropna().astype(str).unique())
                selected_venue = st.selectbox("📍 Точка:", ["Все"] + venues, index=0)
                if selected_venue != "Все":
                    df_full = df_full[df_full[venue_col].astype(str) == selected_venue]
            else:
                st.info("Колонка заведения не найдена, фильтр по точкам отключен.")
                
            # 2. Date Filter
            min_date = df_full['Дата_Отчета'].min().date()
            max_date = df_full['Дата_Отчета'].max().date()
            
            period_mode = st.radio(
                "Период:",
                ["📌 Последний загруженный день", "📅 Месяц (Сравнение)", "📆 Диапазон"],
                horizontal=True,
                index=0
            )
            
            df_current = pd.DataFrame()
            df_prev = pd.DataFrame()
            selected_period = {}
            current_label = ""
            prev_label = ""
            
            if period_mode == "📌 Последний загруженный день":
                 last_day = pd.to_datetime(df_full['Дата_Отчета']).max().normalize()
                 day_start = last_day
                 day_end = last_day + timedelta(hours=23, minutes=59, seconds=59)
                 df_current = df_full[(df_full['Дата_Отчета'] >= day_start) & (df_full['Дата_Отчета'] <= day_end)]
                 df_prev = pd.DataFrame()
                 current_label = f"{last_day.strftime('%d.%m.%Y')} (последний загруженный день)"
                 selected_period = {'start': day_start, 'end': day_end, 'days': 1, 'inflation_start': day_start.replace(day=1)}

            elif period_mode == "📅 Месяц (Сравнение)":
                 df_full['YearMonth'] = df_full['Дата_Отчета'].dt.to_period('M')
                 available_ym = sorted(df_full['YearMonth'].unique(), reverse=True)
                 
                 if not available_ym:
                     st.warning("Нет данных")
                 else:
                     selected_ym = st.selectbox("Месяц:", available_ym)
                     scope_mode = st.radio("Охват:", ["Весь месяц", "По конкретный день"], horizontal=True, label_visibility="collapsed")
                     
                     start_cur = selected_ym.start_time
                     end_cur = selected_ym.end_time
                     
                     if scope_mode == "По конкретный день":
                         max_d = (selected_ym.to_timestamp(how='end')).day
                         selected_day = st.slider("День:", 1, max_d, min(datetime.now().day, max_d))
                         end_cur = start_cur + timedelta(days=selected_day-1)
                         end_cur = end_cur.replace(hour=23, minute=59, second=59)

                     df_current = df_full[(df_full['Дата_Отчета'] >= start_cur) & (df_full['Дата_Отчета'] <= end_cur)]
                     current_label = f"{selected_ym.strftime('%b %Y')} ({scope_mode})"
                     selected_period = {'start': start_cur, 'end': end_cur, 'days': (end_cur - start_cur).days + 1, 'inflation_start': start_cur}
                     
                     compare_mode = st.selectbox("Сравнить с:", ["Предыдущий месяц", "Год назад", "Нет"], index=1)
                     
                     if compare_mode == "Предыдущий месяц":
                         prev_ym = selected_ym - 1
                         start_prev = prev_ym.start_time
                         end_prev = start_prev + (end_cur - start_cur)
                         df_prev = df_full[(df_full['Дата_Отчета'] >= start_prev) & (df_full['Дата_Отчета'] <= end_prev)]
                         prev_label = prev_ym.strftime("%b %Y")
                     elif compare_mode == "Год назад":
                         prev_ym = selected_ym - 12
                         start_prev = prev_ym.start_time
                         end_prev = start_prev + (end_cur - start_cur)
                         df_prev = df_full[(df_full['Дата_Отчета'] >= start_prev) & (df_full['Дата_Отчета'] <= end_prev)]
                         prev_label = prev_ym.strftime("%b %Y")

            else:
                d_range = st.date_input("Диапазон:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
                if isinstance(d_range, tuple) and len(d_range) == 2:
                    s, e = d_range
                    s = pd.to_datetime(s)
                    e = pd.to_datetime(e) + timedelta(hours=23, minutes=59)
                    df_current = df_full[(df_full['Дата_Отчета'] >= s) & (df_full['Дата_Отчета'] <= e)]
                    current_label = f"{s.date()} - {e.date()}"
                    selected_period = {'start': s, 'end': e, 'days': (e - s).days + 1, 'inflation_start': s}
        
        # --- RENDER EXPORT SIDEBAR ---
        if selected_period and 'end' in selected_period:
            export_view.render_sidebar_export(df_current, df_full, tg_token, tg_chat, pd.to_datetime(selected_period['end']))

    else:
        st.info("👈 Загрузите данные в боковом меню.")
        st.stop()

# --- ТЕЛО ОТЧЕТА ---

if not df_current.empty:
    kpi_view.render_kpi(df_current, df_prev, current_label)
    
    # --- SMART INSIGHTS ---
    cur_rev = df_current['Выручка с НДС'].sum()
    prev_rev = df_prev['Выручка с НДС'].sum() if not df_prev.empty else 0
    cur_cost = df_current['Себестоимость'].sum()
    cur_fc = (cur_cost / cur_rev * 100) if cur_rev else 0
    
    with st.expander("💡 Smart Insights", expanded=True):
        insights = analytics_service.calculate_insights(df_current, df_prev, cur_rev, prev_rev, cur_fc)
        for i in insights:
            if i['level'] == 'error': st.error(i['message'])
            elif i['level'] == 'warning': st.warning(i['message'])
            elif i['level'] == 'success': st.success(i['message'])

    # --- TABS ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Выручка (Меню)", "Инфляция С/С", 
        "ABC-анализ", "Симулятор цен", 
        "Дни недели", "Закупки"
    ])
    
    with tab1:
        menu_view.render_menu(df_current, df_prev, current_label, prev_label)
        with st.expander("🔬 Расширенные разделы", expanded=False):
            adv_tab = st.radio("Дополнительно", ["📉 Динамика"], horizontal=True, label_visibility="collapsed")
            if adv_tab == "📉 Динамика":
                menu_view.render_dynamics(df_full, df_current)
    
    with tab2:
        inflation_view.render_inflation(df_full, df_current, selected_period['end'], selected_period['inflation_start'])
        
    with tab3:
        abc_view.render_abc(df_current)
        
    with tab4:
        simulator_view.render_simulator(df_current, df_full)
        
    with tab5:
        weekday_view.render_weekdays(df_current, df_prev, current_label, prev_label)
        
    with tab6:
        procurement_view.render_procurement_v2(df_current, df_full, selected_period['days'])

else:
    from streamlit_lottie import st_lottie
    import requests
    
    @st.cache_data
    def load_lottieurl(url: str):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return r.json()
        except:
            return None
            
    # Lottie "No Data / Empty" animation (a standard clean one from lottiefiles)
    lottie_empty = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_a1xjeug1.json")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if lottie_empty:
            st_lottie(lottie_empty, height=300, key="empty_data")
        st.markdown(
            "<h3 style='text-align: center; color: var(--text-soft);'>Нет данных за выбранный период</h3>"
            "<p style='text-align: center; color: rgba(255,255,255,0.4);'>Пожалуйста, выберите другие даты или загрузите новые данные из источника.</p>",
            unsafe_allow_html=True
        )
