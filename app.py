import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os

from infrastructure.observability import setup_observability
setup_observability()

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
from use_cases import auth_flow, bootstrap, report_flow
from views import admin_view, login_view
from datetime import datetime
import time

_APP_START_TIME = time.perf_counter()

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="RestoAnalytics: Место", layout="wide", initial_sidebar_state="expanded")

# --- ВОРОНКА БЕЗОПАСНОСТИ (PROD HARDENING) ---
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "False").lower() == "true"
TRUST_PROXY = os.getenv("TRUST_PROXY", "False").lower() == "true"

# Health Check (Basic load-balancer heartbeat)
if st.query_params.get("health") == "1":
    st.write({"status": "ok", "version": "1.0", "uptime": datetime.utcnow().isoformat()})
    st.stop()

def get_client_ip():
    """Extract IP honoring TRUST_PROXY ENV for reverse proxies."""
    if TRUST_PROXY:
        forwarded = st.context.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = st.context.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
    return "127.0.0.1" # Streamlit doesn't natively expose direct IP easily without headers

# Enforce HTTPS redirect strictly if demanded
if FORCE_HTTPS:
    proto = st.context.headers.get("x-forwarded-proto", "http").lower()
    if proto != "https":
         # In a true proxy environment, we warn/halt or tell Nginx to redirect. 
         # Since Streamlit cannot easily issue 301 natively midway, we halt.
         st.error("🚨 Insecure Connection / Небезопасное соединение. Пожалуйста, используйте HTTPS.")
         st.stop()

# Emulate Basic Security Headers via HTML injection (where possible)
components.html(
    """
    <script>
    // Streamlit prevents raw HTTP header mutation from the python script layer,
    // but we can enforce frontend frame/sniff policies via DOM meta injections securely.
    var meta1 = document.createElement('meta');
    meta1.httpEquiv = "X-Content-Type-Options";
    meta1.content = "nosniff";
    document.getElementsByTagName('head')[0].appendChild(meta1);
    
    var meta2 = document.createElement('meta');
    meta2.httpEquiv = "X-Frame-Options";
    meta2.content = "DENY";
    document.getElementsByTagName('head')[0].appendChild(meta2);
    
    var meta3 = document.createElement('meta');
    meta3.name = "referrer";
    meta3.content = "no-referrer";
    document.getElementsByTagName('head')[0].appendChild(meta3);
    </script>
    """,
    height=0,
)


# --- СТИЛИ И ЭФФЕКТЫ ---
ui.setup_style()
ui.setup_parallax()

# --- STARTUP ORCHESTRATION ---
startup_result = bootstrap.run_startup()
if startup_result.status == "STOP":
    st.stop()

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

# Build Sentry Context
try:
    import sentry_sdk
    if sentry_sdk.Hub.current.client:
        sentry_sdk.set_user({"id": st.session_state.auth_user.id, "role": st.session_state.auth_user.role, "username": st.session_state.auth_user.login})
except (ImportError, AttributeError):
    pass

st.title(f"📊 Аналитика: {st.session_state.auth_user.full_name}")

# --- DATA & COMPUTE CACHING ---
@st.cache_data(show_spinner=False)
def _cached_build_report_context(_df_full, data_version, period_mode, selected_ym, scope_mode, selected_day, compare_mode, date_range=None):
    return report_flow.build_report_context(
        _df_full, period_mode, selected_ym=selected_ym, scope_mode=scope_mode, selected_day=selected_day, compare_mode=compare_mode, date_range=date_range
    )

@st.cache_data(show_spinner=False)
def _cached_calculate_insights(_df_curr, _df_prev, data_version, cur_rev, prev_rev, cur_fc):
    return analytics_service.calculate_insights(_df_curr, _df_prev, cur_rev, prev_rev, cur_fc)

# Safe defaults for headless/bare imports where st.stop() might not halt execution.
df_current = pd.DataFrame()
df_prev = pd.DataFrame()
selected_period = None
current_label = ""
prev_label = ""

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
                    from use_cases import rbac_policy
                    if not rbac_policy.enforce(st.session_state.auth_user, "SYNC_DATA"):
                        st.error("Недостаточно прав для выполнения синхронизации.")
                    else:
                        ui.show_loading_overlay("Связываюсь с облаком...")
                        success, msg = data_loader.download_and_process_yandex(yd_token, st.session_state.yandex_path)
                        if success:
                            st.success("Данные обновлены!")
                            st.session_state.dropped_stats = data_loader.get_last_sync_meta().get(
                                "dropped_stats",
                                {"count": 0, "cost": 0.0, "items": []},
                            )
                            st.session_state.data_version = st.session_state.get('data_version', 1) + 1
                            st.session_state.df_full = None
                            st.rerun()
                        else:
                            st.error(msg)
        elif source_type == "📂 Локальная папка":
            if st.button("🔄 Загрузить из кэша"):
                 st.session_state.data_version = st.session_state.get('data_version', 1) + 1
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
                     with st.spinner("Загрузка и подготовка данных..."):
                         if True:
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
            
            report_context = report_flow.ReportContext()
            
            if True:
                if period_mode == "📌 Последний загруженный день":
                    report_context = _cached_build_report_context(
                        df_full,
                        id(df_full),
                        period_mode,
                        None,
                        "",
                        None,
                        "",
                        None
                    )

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
                         else:
                             selected_day = None
                         
                         compare_mode = st.selectbox("Сравнить с:", ["Предыдущий месяц", "Год назад", "Нет"], index=1)
                         report_context = _cached_build_report_context(
                            df_full,
                            id(df_full),
                            period_mode,
                            selected_ym,
                            scope_mode,
                            selected_day,
                            compare_mode,
                            None
                        )

                else: # "Диапазон"
                    d_range = st.date_input("Диапазон:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
                    report_context = _cached_build_report_context(
                        df_full,
                        id(df_full),
                        period_mode,
                        None,
                        "",
                        None,
                        "",
                        d_range if isinstance(d_range, tuple) and len(d_range) == 2 else None,
                    )

                df_current = report_context.df_current
                df_prev = report_context.df_prev
                selected_period = report_context.selected_period
                current_label = report_context.current_label
                prev_label = report_context.prev_label
        
        # --- RENDER EXPORT SIDEBAR ---
        if selected_period is not None:
            export_view.render_sidebar_export(df_current, df_full, tg_token, tg_chat, pd.to_datetime(selected_period.end))

        # --- BUILD CACHE KEY SIGNATURE ---
        from utils.signature import build_selection_signature
        
        selection_signature = build_selection_signature(
            venue=selected_venue if 'selected_venue' in locals() else "Все",
            period_mode=period_mode if 'period_mode' in locals() else "Произвольный",
            start_date=selected_period.start if 'selected_period' in locals() and selected_period else None,
            end_date=selected_period.end if 'selected_period' in locals() and selected_period else None,
            compare_mode=compare_mode if 'compare_mode' in locals() else "None"
        )
        if os.environ.get("DEBUG_TIMINGS") == "1":
            print(f"[DEBUG] prev_mode/venue cached signature: {selection_signature}")
        
        st.divider()
        
        # Sentry telemetry tracking
        try:
            import sentry_sdk
            if sentry_sdk.Hub.current.client:
                sentry_sdk.set_tag("app.tab", st.session_state.get("nav_tab", "Unknown"))
        except (ImportError, AttributeError):
            pass

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
        if True:
            insights = _cached_calculate_insights(df_current, df_prev, id(df_current), cur_rev, prev_rev, cur_fc)
        for i in insights:
            if i.level == 'error': st.error(i.message)
            elif i.level == 'warning': st.warning(i.message)
            elif i.level == 'success': st.success(i.message)

    # --- MAIN VIEW ---
    st.divider()
    
    # --- CENTRAL NAVIGATION (PILLS AS TABS) (ISOLATED FRAGMENT) ---
    if 'nav_tab' not in st.session_state:
        st.session_state["nav_tab"] = list(report_flow.REPORT_TAB_LABELS)[0]

    @st.fragment
    def _render_navigation_and_route(_df_curr, _df_p, _cur_l, _prev_l, _df_f, _sel_p, _sig):

        if os.getenv("DEBUG_NAV_TRACE", "0") == "1":
            st.write(f"🔍 DEBUG_NAV_TRACE: Fragment rerunning. st.session_state.nav_tab = {st.session_state.get('nav_tab')}")

        # Render Pills. The key="nav_tab" ensures st.session_state is the SSOT.
        st.pills(
            "Навигация",
            options=list(report_flow.REPORT_TAB_LABELS),
            selection_mode="single",
            default=st.session_state["nav_tab"],
            key="nav_tab",
            label_visibility="collapsed"
        )
        
        # Safe read without mutating the bound widget key
        active_tab = st.session_state.get("nav_tab") or list(report_flow.REPORT_TAB_LABELS)[0]

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        route = report_flow.select_report_route(active_tab)
        
        if True:
            if route == report_flow.ReportRoute.MENU:
                menu_view.render_menu(_df_curr, _df_p, _cur_l, _prev_l, _sig)
                
                with st.expander("🔬 Расширенные разделы", expanded=False):
                    adv_tab = st.radio("Дополнительно", ["📉 Динамика"], horizontal=True, label_visibility="collapsed")
                    if adv_tab == "📉 Динамика":
                        menu_view.render_dynamics(_df_f, _df_curr)
            elif route == report_flow.ReportRoute.INFLATION and _sel_p:
                inflation_view.render_inflation(_df_f, _df_curr, _sel_p.end, _sel_p.inflation_start, _sig)
            elif route == report_flow.ReportRoute.ABC:
                abc_view.render_abc(_df_curr, _sig)
            elif route == report_flow.ReportRoute.SIMULATOR:
                simulator_view.render_simulator(_df_curr, _df_f)
            elif route == report_flow.ReportRoute.WEEKDAYS:
                weekday_view.render_weekdays(_df_curr, _df_p, _cur_l, _prev_l)
            elif route == report_flow.ReportRoute.PROCUREMENT and _sel_p:
                procurement_view.render_procurement_v2(_df_curr, _df_f, _sel_p.days)
                
    # Execute the fragment
    _render_navigation_and_route(df_current, df_prev, current_label, prev_label, df_full, selected_period, selection_signature)



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
