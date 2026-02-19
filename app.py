import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os
import telegram_utils
from services import data_loader, analytics_service, category_service
import auth
import ui
from views import admin_view, login_view, reports_view
from datetime import datetime, timedelta

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="RestoAnalytics: Место", layout="wide", initial_sidebar_state="expanded")

# --- СТИЛИ И ЭФФЕКТЫ ---
ui.setup_style()
ui.setup_parallax()

# --- АВТОМАТИЗАЦИЯ И БД ---
auth.init_auth_db()
auth.bootstrap_admin()

# --- СОСТОЯНИЕ (SESSION STATE) ---
if 'df_full' not in st.session_state:
    st.session_state.df_full = None
if 'dropped_stats' not in st.session_state:
    st.session_state.dropped_stats = {'count': 0, 'cost': 0.0, 'items': []}
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'auth_user' not in st.session_state:
    st.session_state.auth_user = None
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'df_version' not in st.session_state:
    st.session_state.df_version = 0
if 'categories_applied_sig' not in st.session_state:
    st.session_state.categories_applied_sig = None
if 'view_cache' not in st.session_state:
    st.session_state.view_cache = {}
if 'yandex_path' not in st.session_state:
    st.session_state.yandex_path = "RestoAnalytic"
if 'edit_yandex_path' not in st.session_state:
    st.session_state.edit_yandex_path = False
if 'admin_fullscreen' not in st.session_state:
    st.session_state.admin_fullscreen = False
if 'admin_fullscreen_tab' not in st.session_state:
    st.session_state.admin_fullscreen_tab = None
if 'categories_synced' not in st.session_state:
    st.session_state.categories_synced = False
if 'users_synced' not in st.session_state:
    st.session_state.users_synced = False

def clear_browser_auth_token():
    components.html(
        """
        <script>
          document.cookie = "resto_auth_token=; path=/; max-age=0; SameSite=Lax";
          localStorage.removeItem("resto_auth_token");
          sessionStorage.removeItem("resto_auto_login_attempted");
        </script>
        """,
        height=0,
    )

# --- ВХОД / АВТОРИЗАЦИЯ ---
# 1. Проверяем cookie (Refresh / новый рендер)
if st.session_state.auth_user is None:
    current_ua = st.context.headers.get("user-agent")
    token_from_cookie = st.context.cookies.get("resto_auth_token")
    if token_from_cookie:
        from urllib.parse import unquote
        token_from_cookie = unquote(token_from_cookie)
        uid = auth.resolve_runtime_session(token_from_cookie, user_agent=current_ua)
        if uid is not None:
            restored = auth.get_user_by_id(uid)
            if restored and restored[6] == "approved":
                st.session_state.auth_user = {
                    "id": restored[0],
                    "full_name": restored[1],
                    "login": restored[2],
                    "role": restored[5],
                    "status": restored[6],
                }
                st.session_state.auth_token = token_from_cookie

# 2. Если все еще не вошли -> Показываем логин
if st.session_state.auth_user is None:
    login_view.render_auth_screen()
    st.stop()

# 3. Валидация текущей сессии
if st.session_state.auth_user is not None:
    fresh_user = auth.get_user_by_id(st.session_state.auth_user["id"])
    if not fresh_user or fresh_user[6] != "approved":
        if st.session_state.auth_token:
            auth.drop_runtime_session(st.session_state.auth_token)
        clear_browser_auth_token()
        st.session_state.auth_user = None
        st.session_state.auth_token = None
        st.warning("Доступ отозван или аккаунт не одобрен.")
        login_view.render_auth_screen()
        st.stop()

    st.session_state.auth_user.update({
        "id": fresh_user[0],
        "full_name": fresh_user[1],
        "login": fresh_user[2],
        "role": fresh_user[5],
        "status": fresh_user[6],
    })
    
    if st.session_state.auth_token is None:
        st.session_state.auth_token = auth.create_runtime_session(
            fresh_user[0],
            user_agent=st.context.headers.get("user-agent"),
        )
        
    st.session_state.is_admin = st.session_state.auth_user.get("role") == "admin"

# --- AUTO SYNC CATEGORIES FROM YANDEX ---
if not st.session_state.categories_synced:
    yd_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
    if yd_token:
        category_service.sync_from_yandex(yd_token)
    st.session_state.categories_synced = True

# --- AUTO SYNC USERS DB FROM YANDEX ---
if not st.session_state.users_synced:
    yd_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
    if yd_token:
        auth.sync_users_from_yandex(yd_token)
    st.session_state.users_synced = True

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
        if st.session_state.auth_token:
            auth.drop_runtime_session(st.session_state.auth_token)
        clear_browser_auth_token()
        st.session_state.auth_user = None
        st.session_state.auth_token = None
        st.rerun()

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
                     df = pd.read_parquet(data_loader.CACHE_FILE)
                     # Always re-apply categories from current mapping,
                     # so category edits survive app/server restarts.
                     df = category_service.apply_categories(df)
                     st.session_state.df_full = df
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
            target_date = datetime.now()
            period_title_base = ""
            prev_label = ""
            inflation_start_date = None
            
            if period_mode == "📌 Последний загруженный день":
                 last_day = pd.to_datetime(df_full['Дата_Отчета']).max().normalize()
                 day_start = last_day
                 day_end = last_day + timedelta(hours=23, minutes=59, seconds=59)
                 df_current = df_full[(df_full['Дата_Отчета'] >= day_start) & (df_full['Дата_Отчета'] <= day_end)]
                 df_prev = pd.DataFrame()
                 period_title_base = f"{last_day.strftime('%d.%m.%Y')} (последний загруженный день)"
                 target_date = day_end
                 inflation_start_date = day_start.replace(day=1)

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
                     period_title_base = f"{selected_ym.strftime('%b %Y')} ({scope_mode})"
                     target_date = end_cur
                     inflation_start_date = start_cur
                     
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
                    period_title_base = f"{s.date()} - {e.date()}"
                    target_date = e
                    inflation_start_date = s
        
        # --- RENDER EXPORT SIDEBAR ---
        reports_view.render_sidebar_export(df_current, df_full, tg_token, tg_chat, pd.to_datetime(target_date))

    else:
        st.info("👈 Загрузите данные в боковом меню.")
        st.stop()

# --- ТЕЛО ОТЧЕТА ---

if not df_current.empty:
    reports_view.render_kpi(df_current, df_prev, period_title_base)
    
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
    tab_options = ["🔥 Инфляция", "🍰 Меню и Косты", "⭐ Матрица (ABC)", "🗓 Дни недели", "📦 Закупки", "🔮 Симулятор"]
    selected_tab = st.radio("Раздел:", tab_options, horizontal=True, label_visibility="collapsed")
    st.divider()
    
    if selected_tab == "🔥 Инфляция":
        reports_view.render_inflation(df_full, df_current, target_date, inflation_start_date)
            
    elif selected_tab == "🍰 Меню и Косты":
        reports_view.render_menu(df_current, df_prev, period_title_base, prev_label)
            
    elif selected_tab == "⭐ Матрица (ABC)":
        reports_view.render_abc(df_current)
        
    elif selected_tab == "🗓 Дни недели":
        reports_view.render_weekdays(df_current, df_prev, period_title_base, prev_label)
            

    elif selected_tab == "📦 Закупки":
        # New Procurement Logic
        # We need period_days. Calculate from period_title_base or df_current dates
        if not df_current.empty:
            d_min = df_current['Дата_Отчета'].min()
            d_max = df_current['Дата_Отчета'].max()
            days = (d_max - d_min).days + 1
        else:
            days = 1
        reports_view.render_procurement_v2(df_current, df_full, days)

        
    elif selected_tab == "🔮 Симулятор":
        reports_view.render_simulator(df_current, df_full)

    if selected_tab == "🍰 Меню и Косты":
        with st.expander("🔬 Расширенные разделы", expanded=False):
            adv_tab = st.radio("Дополнительно", ["📉 Динамика"], horizontal=True, label_visibility="collapsed")
            if adv_tab == "📉 Динамика":
                reports_view.render_dynamics(df_full, df_current)

else:
    st.warning("Нет данных за выбранный период.")
