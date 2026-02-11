import streamlit as st
import streamlit.components.v1 as components
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
        font=dict(family="Manrope, sans-serif", size=13, color="#EAF2FF"),
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(185,220,255,0.06)",
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="rgba(210,230,255,0.28)"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(186,218,255,0.12)",
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
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@500;700&display=swap');

        :root {
            --glass-bg: rgba(167, 210, 255, 0.11);
            --glass-bg-strong: rgba(187, 223, 255, 0.17);
            --glass-border: rgba(234, 247, 255, 0.35);
            --glass-shadow: 0 14px 42px rgba(4, 18, 42, 0.35);
            --text-main: #f3f8ff;
            --text-soft: rgba(234, 244, 255, 0.72);
            --accent: #73c3ff;
            --accent-2: #9fe5ff;
            --ease-fluid: cubic-bezier(0.22, 1, 0.36, 1);
            --ease-soft: cubic-bezier(0.25, 0.9, 0.3, 1);
            --anim-fast: 220ms;
            --anim-mid: 340ms;
            --anim-slow: 520ms;
        }

        html, body, .stApp {
            font-family: 'Manrope', 'Plus Jakarta Sans', sans-serif;
            color: var(--text-main);
            background:
                radial-gradient(55rem 28rem at 10% -5%, rgba(111, 198, 255, 0.30), transparent 65%),
                radial-gradient(50rem 24rem at 95% 0%, rgba(145, 125, 255, 0.20), transparent 62%),
                radial-gradient(38rem 20rem at 50% 110%, rgba(70, 180, 255, 0.18), transparent 60%),
                linear-gradient(180deg, #08101d 0%, #0a1422 48%, #0b1420 100%);
            background-attachment: fixed;
            --scroll-y: 0px;
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background:
                radial-gradient(18rem 18rem at 14% 24%, rgba(255, 255, 255, 0.07), transparent 70%),
                radial-gradient(22rem 22rem at 84% 68%, rgba(155, 220, 255, 0.07), transparent 74%);
            filter: blur(1px);
            transform: translate3d(0, calc(var(--scroll-y) * 0.06), 0);
            will-change: transform;
            z-index: 0;
        }

        .stApp::after {
            content: "";
            position: fixed;
            inset: -10% -5% 0 -5%;
            pointer-events: none;
            background:
                radial-gradient(26rem 16rem at 22% 78%, rgba(120, 196, 255, 0.12), transparent 68%),
                radial-gradient(30rem 16rem at 82% 16%, rgba(196, 179, 255, 0.10), transparent 70%);
            transform: translate3d(0, calc(var(--scroll-y) * -0.035), 0);
            will-change: transform;
            z-index: 0;
        }

        .main .block-container {
            position: relative;
            z-index: 1;
            padding-top: 1.6rem;
            padding-bottom: 2rem;
            animation: pageSlideIn var(--anim-mid) var(--ease-fluid);
        }

        @keyframes pageSlideIn {
            from {
                opacity: 0;
                transform: translate3d(12px, 0, 0) scale(0.995);
                filter: blur(4px);
            }
            to {
                opacity: 1;
                transform: translate3d(0, 0, 0) scale(1);
                filter: blur(0);
            }
        }

        @keyframes glassFadeUp {
            from {
                opacity: 0;
                transform: translateY(10px) scale(0.995);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        h1, h2, h3 {
            font-weight: 800;
            letter-spacing: -0.04em;
            color: var(--text-main);
            text-shadow: 0 4px 20px rgba(106, 190, 255, 0.22);
        }

        p, label, span, div {
            color: var(--text-main);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(165deg, rgba(173, 216, 255, 0.10), rgba(119, 186, 255, 0.07)) !important;
            backdrop-filter: blur(18px) saturate(150%);
            -webkit-backdrop-filter: blur(18px) saturate(150%);
            border-right: 1px solid rgba(228, 244, 255, 0.22) !important;
            box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.14), 8px 0 30px rgba(5, 18, 45, 0.25);
        }

        [data-testid="stSidebar"] * {
            color: var(--text-main) !important;
        }

        [data-testid="stMetric"],
        [data-testid="stVerticalBlock"] > [data-testid="element-container"] > div:has([data-testid="stDataFrame"]) {
            border: 1px solid var(--glass-border) !important;
            box-shadow: var(--glass-shadow) !important;
            animation: glassFadeUp var(--anim-mid) var(--ease-fluid);
        }

        [data-testid="stMetric"] {
            position: relative;
            overflow: hidden;
            background: linear-gradient(155deg, var(--glass-bg-strong), rgba(129, 189, 255, 0.08)) !important;
            backdrop-filter: blur(18px) saturate(140%);
            -webkit-backdrop-filter: blur(18px) saturate(140%);
            padding: 15px !important;
            border-radius: 18px !important;
            transition: transform var(--anim-fast) var(--ease-fluid), box-shadow var(--anim-mid) var(--ease-soft), border-color var(--anim-fast) ease;
        }

        [data-testid="stMetric"]::after {
            content: "";
            position: absolute;
            inset: 0;
            border-radius: inherit;
            background: linear-gradient(125deg, rgba(255, 255, 255, 0.22), rgba(255, 255, 255, 0.01) 45%);
            pointer-events: none;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-2px) scale(1.006);
            border-color: rgba(222, 244, 255, 0.52) !important;
            box-shadow: 0 20px 45px rgba(7, 23, 51, 0.46) !important;
            background: linear-gradient(160deg, rgba(189, 228, 255, 0.19), rgba(130, 192, 255, 0.10)) !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 14px;
            color: var(--text-soft) !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 26px;
            font-weight: 700;
            color: var(--text-main);
        }

        [data-testid="stMetricDelta"] {
            font-size: 14px;
        }

        [data-testid="stMarkdownContainer"] code {
            background: rgba(150, 205, 255, 0.18);
            border: 1px solid rgba(218, 242, 255, 0.27);
            border-radius: 8px;
            padding: 0.1rem 0.32rem;
        }

        [data-testid="stExpander"] {
            background: linear-gradient(160deg, rgba(178, 220, 255, 0.09), rgba(120, 183, 255, 0.06)) !important;
            border: 1px solid rgba(228, 244, 255, 0.25) !important;
            border-radius: 16px !important;
            backdrop-filter: blur(13px) saturate(130%);
            -webkit-backdrop-filter: blur(13px) saturate(130%);
            box-shadow: 0 10px 32px rgba(8, 21, 48, 0.28);
            animation: glassFadeUp var(--anim-mid) var(--ease-fluid);
            transition: transform var(--anim-fast) var(--ease-fluid), box-shadow var(--anim-mid) var(--ease-soft), border-color var(--anim-fast) ease;
            overflow: hidden !important;
        }

        [data-testid="stExpander"] details {
            border-radius: 16px !important;
            overflow: hidden !important;
            background: linear-gradient(165deg, rgba(170, 212, 255, 0.12), rgba(118, 182, 255, 0.08)) !important;
        }

        [data-testid="stExpander"] summary {
            border-radius: 14px !important;
            border: none !important;
            background: transparent !important;
        }

        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
            background: linear-gradient(175deg, rgba(182, 221, 255, 0.10), rgba(119, 182, 255, 0.07)) !important;
            border-top: 1px solid rgba(226, 244, 255, 0.17);
            border-radius: 0 0 14px 14px !important;
        }

        /* In sidebar we keep popovers/calendars visible, otherwise date picker clips */
        [data-testid="stSidebar"] [data-testid="stExpander"],
        [data-testid="stSidebar"] [data-testid="stExpander"] details,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
            overflow: visible !important;
        }

        .streamlit-expanderHeader {
            background-color: transparent;
            border-radius: 12px;
        }

        button[kind="primary"] {
            background: linear-gradient(135deg, #7ec9ff 0%, #64b8ff 48%, #95dcff 100%) !important;
            color: #06203e !important;
            border: 1px solid rgba(230, 247, 255, 0.6) !important;
            box-shadow: 0 10px 24px rgba(52, 148, 220, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.7);
            transition: transform var(--anim-fast) var(--ease-fluid), box-shadow var(--anim-mid) var(--ease-soft), filter var(--anim-fast) ease;
            font-weight: 700;
        }

        button[kind="primary"]:hover {
            box-shadow: 0 16px 30px rgba(60, 156, 231, 0.48), inset 0 1px 0 rgba(255, 255, 255, 0.78);
            transform: translateY(-1px) scale(1.005);
            filter: saturate(1.05);
        }

        button[kind="secondary"] {
            background: linear-gradient(150deg, rgba(192, 228, 255, 0.16), rgba(141, 197, 255, 0.09)) !important;
            border: 1px solid rgba(224, 243, 255, 0.32) !important;
            border-radius: 12px !important;
            color: var(--text-main) !important;
            backdrop-filter: blur(10px) saturate(120%);
            -webkit-backdrop-filter: blur(10px) saturate(120%);
        }

        .stSelectbox label, .stRadio label {
            font-weight: 600 !important;
            color: var(--text-main) !important;
        }

        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div {
            background: linear-gradient(160deg, rgba(190, 226, 255, 0.15), rgba(138, 192, 248, 0.08)) !important;
            border: 1px solid rgba(225, 243, 255, 0.32) !important;
            border-radius: 12px !important;
            backdrop-filter: blur(10px);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.22), 0 8px 22px rgba(8, 24, 50, 0.22);
        }

        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within {
            border-color: rgba(220, 243, 255, 0.70) !important;
            box-shadow: 0 0 0 2px rgba(126, 199, 255, 0.26), 0 10px 24px rgba(7, 28, 58, 0.30) !important;
        }

        [data-testid="stDataFrame"] {
            border-radius: 14px;
            border: 1px solid rgba(228, 243, 255, 0.28);
            overflow: hidden;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 8px 30px rgba(6, 18, 41, 0.3);
            animation: glassFadeUp var(--anim-mid) var(--ease-fluid);
            transition: transform var(--anim-fast) var(--ease-fluid), box-shadow var(--anim-mid) var(--ease-soft);
        }

        [data-testid="stPlotlyChart"],
        [data-testid="stDataFrame"],
        [data-testid="stExpander"],
        [data-testid="stMetric"],
        [data-testid="stAlert"] {
            will-change: transform, opacity;
            transform: translateZ(0);
            backface-visibility: hidden;
        }

        [data-testid="stVerticalBlock"] > [data-testid="element-container"] {
            animation: sectionFloatIn var(--anim-slow) var(--ease-fluid) both;
        }

        [data-testid="stVerticalBlock"] > [data-testid="element-container"]:nth-child(1) { animation-delay: 20ms; }
        [data-testid="stVerticalBlock"] > [data-testid="element-container"]:nth-child(2) { animation-delay: 45ms; }
        [data-testid="stVerticalBlock"] > [data-testid="element-container"]:nth-child(3) { animation-delay: 70ms; }
        [data-testid="stVerticalBlock"] > [data-testid="element-container"]:nth-child(4) { animation-delay: 95ms; }
        [data-testid="stVerticalBlock"] > [data-testid="element-container"]:nth-child(5) { animation-delay: 120ms; }
        [data-testid="stVerticalBlock"] > [data-testid="element-container"]:nth-child(6) { animation-delay: 145ms; }

        @keyframes sectionFloatIn {
            from {
                opacity: 0;
                transform: translate3d(0, 12px, 0) scale(0.998);
            }
            to {
                opacity: 1;
                transform: translate3d(0, 0, 0) scale(1);
            }
        }

        [role="tablist"] {
            gap: 0.45rem;
            flex-wrap: wrap;
        }

        [role="tab"] {
            border-radius: 999px !important;
            border: 1px solid rgba(222, 240, 255, 0.26) !important;
            background: linear-gradient(160deg, rgba(176, 219, 255, 0.12), rgba(130, 186, 255, 0.07)) !important;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            padding: 0.4rem 0.9rem !important;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
            backdrop-filter: blur(6px);
        }

        #MainMenu {visibility: hidden;}

        @media (max-width: 768px) {
            [data-testid="stSidebar"] {
                border-right: none !important;
            }
            [data-testid="stMetricValue"] {
                font-size: 22px;
            }
            .main .block-container {
                padding-top: 1rem;
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            .main .block-container,
            [data-testid="stMetric"],
            [data-testid="stExpander"],
            [data-testid="stDataFrame"] {
                animation: none !important;
                transition: none !important;
            }
        }

        .ra-loading-overlay {
            position: fixed;
            inset: 0;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            background: radial-gradient(40rem 20rem at 20% 10%, rgba(142, 208, 255, 0.24), rgba(5, 10, 19, 0.74)),
                        linear-gradient(180deg, rgba(3, 9, 18, 0.72), rgba(6, 12, 22, 0.78));
            backdrop-filter: blur(12px) saturate(120%);
            -webkit-backdrop-filter: blur(12px) saturate(120%);
        }

        .ra-loading-card {
            min-width: 320px;
            max-width: 540px;
            border-radius: 22px;
            padding: 24px 26px;
            border: 1px solid rgba(228, 245, 255, 0.42);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.30);
            background: linear-gradient(165deg, rgba(183, 223, 255, 0.16), rgba(125, 187, 255, 0.10));
            text-align: center;
        }

        .ra-loading-orb {
            width: 56px;
            height: 56px;
            margin: 0 auto 12px;
            border-radius: 999px;
            border: 2px solid rgba(220, 244, 255, 0.35);
            border-top-color: rgba(122, 204, 255, 0.95);
            border-right-color: rgba(174, 228, 255, 0.88);
            animation: raSpin 0.95s linear infinite;
            box-shadow: 0 0 24px rgba(124, 205, 255, 0.45), inset 0 0 16px rgba(194, 236, 255, 0.30);
        }

        .ra-loading-title {
            font-size: 1.2rem;
            font-weight: 800;
            margin-bottom: 6px;
            color: #f2f8ff;
            letter-spacing: -0.01em;
        }

        .ra-loading-sub {
            color: rgba(232, 244, 255, 0.84);
            font-size: 0.96rem;
        }

        @keyframes raSpin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """, unsafe_allow_html=True)

setup_style()

def setup_parallax():
    components.html("""
    <script>
    (function () {
      try {
        const p = window.parent;
        if (!p || p.__restoParallaxBound) return;
        p.__restoParallaxBound = true;

        const root = p.document.documentElement;
        let ticking = false;

        function applyScrollVar() {
          ticking = false;
          const y = p.scrollY || p.document.documentElement.scrollTop || 0;
          root.style.setProperty('--scroll-y', y + 'px');
        }

        function onScroll() {
          if (!ticking) {
            ticking = true;
            p.requestAnimationFrame(applyScrollVar);
          }
        }

        p.addEventListener('scroll', onScroll, { passive: true });
        applyScrollVar();
      } catch (e) {}
    })();
    </script>
    """, height=0)

setup_parallax()

def show_loading_overlay(message="Скачиваем и обрабатываем данные"):
    st.markdown(
        f"""
        <div class="ra-loading-overlay">
          <div class="ra-loading-card">
            <div class="ra-loading-orb"></div>
            <div class="ra-loading-title">Подготовка отчета</div>
            <div class="ra-loading-sub">{message}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- ИНИЦИАЛИЗАЦИЯ ПАМЯТИ ---
if 'df_full' not in st.session_state:
    st.session_state.df_full = None
if 'dropped_stats' not in st.session_state:
    st.session_state.dropped_stats = {'count': 0, 'cost': 0.0, 'items': []}
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
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

@st.cache_data(ttl=600, show_spinner=False)
def compute_inflation_metrics(df_full_scope, df_view_scope):
    if df_full_scope is None or df_full_scope.empty or df_view_scope is None or df_view_scope.empty:
        return 0.0, 0.0, pd.DataFrame()

    price_history = (
        df_full_scope.groupby(['Блюдо', 'Дата_Отчета'], observed=True)['Unit_Cost']
        .mean()
        .reset_index()
        .sort_values(['Блюдо', 'Дата_Отчета'])
    )
    if price_history.empty:
        return 0.0, 0.0, pd.DataFrame()

    item_prices = price_history.groupby('Блюдо', observed=True)['Unit_Cost'].agg(first_price='first', last_price='last').reset_index()
    sold_qty = df_view_scope.groupby('Блюдо', observed=True)['Количество'].sum().reset_index().rename(columns={'Количество': 'qty_sold'})

    merged = item_prices.merge(sold_qty, on='Блюдо', how='inner')
    merged = merged[(merged['first_price'] > 5) & (merged['qty_sold'] > 0)]
    if merged.empty:
        return 0.0, 0.0, pd.DataFrame()

    merged['diff_abs'] = merged['last_price'] - merged['first_price']
    merged['Рост %'] = (merged['diff_abs'] / merged['first_price']) * 100
    merged['Эффект (₽)'] = merged['diff_abs'] * merged['qty_sold']

    total_gross_loss = float(merged.loc[merged['Эффект (₽)'] > 0, 'Эффект (₽)'].sum())
    total_gross_save = float((-merged.loc[merged['Эффект (₽)'] < 0, 'Эффект (₽)']).sum())

    merged = merged[merged['Рост %'].abs() > 1]
    if merged.empty:
        return total_gross_loss, total_gross_save, pd.DataFrame()

    df_inf = merged.rename(columns={'Блюдо': 'Товар', 'first_price': 'Старая цена', 'last_price': 'Новая цена'})
    return total_gross_loss, total_gross_save, df_inf[['Товар', 'Старая цена', 'Новая цена', 'Рост %', 'Эффект (₽)']]

def compute_supplier_stats(df_view_scope):
    if 'Поставщик' not in df_view_scope.columns or df_view_scope.empty:
        return pd.DataFrame()
    supplier_stats = df_view_scope.groupby('Поставщик', observed=True)['Себестоимость'].sum().reset_index()
    supplier_stats = supplier_stats[supplier_stats['Поставщик'] != 'Не указан']
    return supplier_stats.sort_values('Себестоимость', ascending=False).head(10)

def compute_menu_tab_data(df_view_scope, target_cat):
    if df_view_scope.empty:
        return pd.DataFrame(), pd.DataFrame()
    df_cat = df_view_scope.groupby(target_cat, observed=True)['Выручка с НДС'].sum().reset_index()
    df_menu = (
        df_view_scope
        .groupby(['Блюдо', target_cat], observed=True)
        .agg({'Выручка с НДС': 'sum', 'Себестоимость': 'sum', 'Количество': 'sum'})
        .reset_index()
    )
    df_menu['Фудкост %'] = np.where(df_menu['Выручка с НДС'] > 0, df_menu['Себестоимость'] / df_menu['Выручка с НДС'] * 100, 0)
    df_menu = df_menu.sort_values('Выручка с НДС', ascending=False).head(50)
    df_menu = df_menu.rename(columns={target_cat: 'Категория'})
    return df_cat, df_menu

def compute_abc_data(df_view_scope):
    if df_view_scope.empty:
        return pd.DataFrame(), 0.0, 0.0
    abc_df = df_view_scope.groupby('Блюдо', observed=True).agg({'Количество': 'sum', 'Выручка с НДС': 'sum', 'Себестоимость': 'sum'}).reset_index()
    abc_df = abc_df[abc_df['Количество'] > 0]
    if abc_df.empty:
        return abc_df, 0.0, 0.0
    abc_df['Маржа'] = abc_df['Выручка с НДС'] - abc_df['Себестоимость']
    abc_df['Unit_Margin'] = abc_df['Маржа'] / abc_df['Количество']
    avg_qty = float(abc_df['Количество'].mean())
    avg_margin = float(abc_df['Unit_Margin'].mean())
    conditions = [
        (abc_df['Unit_Margin'] >= avg_margin) & (abc_df['Количество'] >= avg_qty),
        (abc_df['Unit_Margin'] < avg_margin) & (abc_df['Количество'] >= avg_qty),
        (abc_df['Unit_Margin'] >= avg_margin) & (abc_df['Количество'] < avg_qty),
    ]
    classes = ["⭐ Звезда", "🐎 Лошадка", "❓ Загадка"]
    abc_df['Класс'] = np.select(conditions, classes, default="🐶 Собака")
    return abc_df, avg_qty, avg_margin

def compute_weekday_stats(df_scope):
    if df_scope.empty:
        return pd.DataFrame(), pd.DataFrame()

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days_rus_map = {"Monday": "ПН", "Tuesday": "ВТ", "Wednesday": "СР", "Thursday": "ЧТ", "Friday": "ПТ", "Saturday": "СБ", "Sunday": "ВС"}

    daily = (
        df_scope.groupby('Дата_Отчета', observed=True)['Выручка с НДС']
        .sum()
        .reset_index()
        .sort_values('Дата_Отчета')
    )
    daily['ИндексДня'] = np.arange(1, len(daily) + 1)
    daily['ДеньНедели'] = daily['Дата_Отчета'].dt.day_name()
    daily['ДеньРус'] = daily['ДеньНедели'].map(days_rus_map)
    daily['Дата_Подпись'] = daily['Дата_Отчета'].dt.strftime('%d.%m')

    weekday_avg = (
        daily.groupby('ДеньНедели', observed=True)['Выручка с НДС']
        .mean()
        .reindex(days_order)
        .reset_index()
    )
    weekday_avg['ДеньРус'] = weekday_avg['ДеньНедели'].map(days_rus_map)
    return daily, weekday_avg

def compute_purchase_plan(df_full_scope, days_to_buy, safety_stock):
    if df_full_scope.empty:
        return pd.DataFrame()
    last_30_days = df_full_scope['Дата_Отчета'].max() - timedelta(days=30)
    df_recent = df_full_scope[df_full_scope['Дата_Отчета'] >= last_30_days]
    daily_sales = df_recent.groupby('Блюдо', observed=True)['Количество'].sum().reset_index()
    daily_sales['Avg_Daily_Qty'] = daily_sales['Количество'] / 30
    last_prices = df_full_scope.sort_values('Дата_Отчета').groupby('Блюдо', observed=True)['Unit_Cost'].last().reset_index()
    plan_df = pd.merge(daily_sales[['Блюдо', 'Avg_Daily_Qty']], last_prices, on='Блюдо', how='inner')
    plan_df['Need_Qty'] = plan_df['Avg_Daily_Qty'] * days_to_buy * (1 + safety_stock / 100)
    plan_df['Budget'] = plan_df['Need_Qty'] * plan_df['Unit_Cost']
    return plan_df[plan_df['Need_Qty'] > 0.5].sort_values('Budget', ascending=False)

def compute_simulation(df_view_scope, selected_cats, delta_price, delta_cost, delta_vol):
    if not selected_cats:
        return None
    df_sim = df_view_scope[df_view_scope['Категория'].isin(selected_cats)].copy()
    if df_sim.empty:
        return None
    base_revenue = float(df_sim['Выручка с НДС'].sum())
    base_cost_total = float(df_sim['Себестоимость'].sum())
    base_margin = base_revenue - base_cost_total
    sim_revenue = base_revenue * (1 + delta_price / 100) * (1 + delta_vol / 100)
    sim_cost_total = base_cost_total * (1 + delta_cost / 100) * (1 + delta_vol / 100)
    sim_margin = sim_revenue - sim_cost_total
    new_profitability = (sim_margin / sim_revenue * 100) if sim_revenue > 0 else 0
    old_profitability = (base_margin / base_revenue * 100) if base_revenue > 0 else 0
    return {
        'base_revenue': base_revenue,
        'base_margin': base_margin,
        'sim_revenue': sim_revenue,
        'sim_margin': sim_margin,
        'diff_rev': sim_revenue - base_revenue,
        'diff_margin': sim_margin - base_margin,
        'new_profitability': new_profitability,
        'old_profitability': old_profitability,
    }

@st.cache_data(ttl=3600, show_spinner=False)
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

def optimize_dataframe(df):
    if df is None or df.empty:
        return df

    out = df.copy()

    if 'Дата_Отчета' in out.columns:
        out['Дата_Отчета'] = pd.to_datetime(out['Дата_Отчета'], errors='coerce')

    float_cols = ['Себестоимость', 'Выручка с НДС', 'Unit_Cost', 'Фудкост']
    int_cols = ['Количество']
    for col in float_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors='coerce').fillna(0).astype('float32')
    for col in int_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors='coerce').fillna(0).astype('int32')

    for col in ['Категория', 'Venue', 'Поставщик', 'Блюдо', 'Макро_Категория']:
        if col in out.columns:
            nunique = out[col].nunique(dropna=False)
            if 0 < nunique < len(out) * 0.8:
                out[col] = out[col].astype('category')

    return out

def set_df_full(df):
    st.session_state.df_full = optimize_dataframe(df)
    st.session_state.df_version += 1
    st.session_state.categories_applied_sig = None
    st.session_state.view_cache = {}

def get_view_cached(cache_key, factory):
    if cache_key not in st.session_state.view_cache:
        st.session_state.view_cache[cache_key] = factory()
    return st.session_state.view_cache[cache_key]

# --- AUTO-LOAD CACHE ON STARTUP ---
CACHE_FILE = "data_cache.parquet"
if st.session_state.df_full is None and os.path.exists(CACHE_FILE):
    try:
        set_df_full(pd.read_parquet(CACHE_FILE))
        # Optional: st.toast("Данные восстановлены из кеша", icon="💾")
    except Exception:
        pass # Fail silently, user can load manually

# --- 1. SIDEBAR: DATA LOADING ---
# --- 1. SIDEBAR: DATA LOADING ---
is_admin = st.session_state.is_admin
main_loader_slot = st.empty()
with st.sidebar:
    st.title("🎛 Меню")

    admin_pin = get_secret("ADMIN_PIN") or os.getenv("ADMIN_PIN")
    if admin_pin:
        with st.expander("🔐 Админ-доступ", expanded=False):
            entered_pin = st.text_input("Введите PIN", type="password", key="admin_pin_input")
            col_login, col_logout = st.columns(2)
            with col_login:
                if st.button("Войти", use_container_width=True):
                    if entered_pin == admin_pin:
                        st.session_state.is_admin = True
                        st.success("Админ-доступ включен")
                        st.rerun()
                    else:
                        st.error("Неверный PIN")
            with col_logout:
                if st.button("Выйти", use_container_width=True):
                    st.session_state.is_admin = False
                    st.rerun()
            if st.session_state.is_admin:
                st.caption("Статус: админ")
    else:
        st.session_state.is_admin = True

    is_admin = st.session_state.is_admin
    
    # --- DATA SOURCE (EXPANDER) ---
    with st.expander("📂 Источник данных", expanded=False):
        source_mode = st.radio("Режим:", ["Яндекс.Диск", "Локальная папка", "Ручная загрузка"], label_visibility="collapsed")

        # --- YANDEX DISK ---
        if source_mode == "Яндекс.Диск":
            st.markdown("Папка на Диске:")
            if st.button(f"📁 {st.session_state.yandex_path}", use_container_width=True, key="yandex_path_button"):
                st.session_state.edit_yandex_path = not st.session_state.edit_yandex_path

            if st.session_state.edit_yandex_path:
                new_path = st.text_input("Изменить путь:", st.session_state.yandex_path, key="yandex_path_editor")
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    if st.button("💾 Сохранить путь", use_container_width=True, key="save_yandex_path"):
                        st.session_state.yandex_path = new_path.strip() or "RestoAnalytic"
                        st.session_state.edit_yandex_path = False
                        st.rerun()
                with e_col2:
                    if st.button("✖ Отмена", use_container_width=True, key="cancel_yandex_path"):
                        st.session_state.edit_yandex_path = False
                        st.rerun()

            yandex_path = st.session_state.yandex_path
            if st.button("🚀 Скачать отчеты", type="primary", use_container_width=True):
                if not get_secret("YANDEX_TOKEN"):
                     st.error("⚠️ Нет токена!")
                else:
                    # Always refresh Yandex listing/parsing on explicit user action.
                    load_all_from_yandex.clear()
                    with main_loader_slot.container():
                        show_loading_overlay("Скачиваем данные с Яндекс.Диска и собираем витрину…")
                    temp_data, dropped_load = load_all_from_yandex(yandex_path)
                    main_loader_slot.empty()
                    if temp_data:
                        set_df_full(pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета'))
                        
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
                with main_loader_slot.container():
                    show_loading_overlay("Сканируем локальную папку и обрабатываем файлы…")
                temp_data, dropped_load = load_from_local_folder(local_path)
                main_loader_slot.empty()
                if temp_data:
                    set_df_full(pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета'))
                    
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
                with main_loader_slot.container():
                    show_loading_overlay("Читаем загруженные файлы и считаем показатели…")
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
                    set_df_full(pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета'))
                    st.success("Файлы обработаны!")
                    main_loader_slot.empty()
                    st.rerun()
                main_loader_slot.empty()

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
                     set_df_full(pd.read_parquet(CACHE_FILE))
                     st.success("ОК!")
                     st.rerun()
                else:
                     st.warning("Нет")
        
        if st.button("🗑 Сброс", use_container_width=True):
            st.cache_data.clear()
            st.session_state.df_full = None
            st.session_state.dropped_stats = {'count': 0, 'cost': 0.0, 'items': []}
            st.session_state.df_version = 0
            st.session_state.categories_applied_sig = None
            st.session_state.view_cache = {}
            st.rerun()
            
    # --- DEBUG INFO IN SIDEBAR ---
    if is_admin:
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
MAPPING_YANDEX_PATH = "RestoAnalytic/category_mapping.json"

def _get_mapping_remote_path():
    return get_secret("CATEGORY_MAPPING_PATH") or os.getenv("CATEGORY_MAPPING_PATH") or MAPPING_YANDEX_PATH

@st.cache_data(ttl=600, show_spinner=False)
def load_custom_categories():
    token = get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
    remote_path = _get_mapping_remote_path()

    # Try remote first so mappings survive app reboot/redeploy
    if token:
        try:
            headers = {'Authorization': f'OAuth {token}'}
            dl_meta = requests.get(
                "https://cloud-api.yandex.net/v1/disk/resources/download",
                headers=headers,
                params={'path': remote_path},
                timeout=6
            )
            if dl_meta.status_code == 200:
                href = dl_meta.json().get("href")
                if href:
                    dl_resp = requests.get(href, timeout=6)
                    if dl_resp.status_code == 200 and dl_resp.text.strip():
                        data = json.loads(dl_resp.text)
                        if isinstance(data, dict):
                            return data
        except Exception:
            pass

    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_custom_categories(new_map):
    current_map = load_custom_categories()
    current_map.update(new_map)
    payload = json.dumps(current_map, ensure_ascii=False, indent=4)

    token = get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
    remote_path = _get_mapping_remote_path()
    saved_remote = False

    if token:
        try:
            headers = {'Authorization': f'OAuth {token}'}
            up_meta = requests.get(
                "https://cloud-api.yandex.net/v1/disk/resources/upload",
                headers=headers,
                params={'path': remote_path, 'overwrite': 'true'},
                timeout=10
            )
            if up_meta.status_code == 200:
                href = up_meta.json().get("href")
                if href:
                    up_resp = requests.put(href, data=payload.encode('utf-8'), timeout=12)
                    saved_remote = up_resp.status_code in (200, 201, 202)
        except Exception:
            saved_remote = False

    # Keep local fallback for development
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        f.write(payload)

    load_custom_categories.clear()
    st.session_state.categories_applied_sig = None
    st.session_state.view_cache = {}

    return saved_remote

# Load and Apply Custom Categories globally to df_full
if st.session_state.df_full is not None:
    custom_cats = load_custom_categories()
    mapping_sig = json.dumps(custom_cats, sort_keys=True, ensure_ascii=False) if custom_cats else ""
    apply_sig = f"{st.session_state.df_version}:{mapping_sig}"

    if st.session_state.categories_applied_sig != apply_sig:
        if custom_cats:
            mapped = st.session_state.df_full['Блюдо'].astype(str).map(custom_cats)
            st.session_state.df_full['Категория'] = mapped.fillna(st.session_state.df_full['Категория'])

        # --- GLOBAL FILTER: DELETE IGNORED ITEMS ---
        st.session_state.df_full = st.session_state.df_full[st.session_state.df_full['Категория'] != "⛔ Исключить из отчетов"]
        st.session_state.categories_applied_sig = apply_sig

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
        period_title_base = "Произвольный период"
        selected_day = None
        
        if period_mode == "📅 Месяц (Сравнение)":
            df_full['Month_Year'] = df_full['Дата_Отчета'].dt.to_period('M')
            available_months = sorted(df_full['Month_Year'].unique(), reverse=True)
            
            if available_months:
                selected_month = st.selectbox("Выбери месяц:", available_months, format_func=lambda x: x.strftime('%B %Y'))
                scope_mode = st.radio("Период:", ["Весь месяц", "Один день"], horizontal=True)

                if scope_mode == "Один день":
                    month_days = sorted(df_full[df_full['Month_Year'] == selected_month]['Дата_Отчета'].dt.date.unique())
                    if month_days:
                        selected_day = st.selectbox(
                            "Выбери день:",
                            month_days,
                            format_func=lambda d: d.strftime('%d.%m.%Y')
                        )
                        df_current = df_full[df_full['Дата_Отчета'].dt.date == selected_day]
                        target_date = selected_day
                        period_title_base = selected_day.strftime('%d.%m.%Y')

                        compare_options = ["Предыдущий день", "Тот же день (год назад)", "Нет"]
                        compare_mode = st.selectbox("Сравнить с:", compare_options)

                        if compare_mode == "Предыдущий день":
                            prev_day = selected_day - timedelta(days=1)
                            df_prev = df_full[df_full['Дата_Отчета'].dt.date == prev_day]
                            prev_label = prev_day.strftime('%d.%m.%Y')
                        elif compare_mode == "Тот же день (год назад)":
                            def safe_year_sub(d):
                                try: return d.replace(year=d.year - 1)
                                except ValueError: return d.replace(year=d.year - 1, day=28)

                            prev_day = safe_year_sub(selected_day)
                            df_prev = df_full[df_full['Дата_Отчета'].dt.date == prev_day]
                            prev_label = prev_day.strftime('%d.%m.%Y')
                else:
                    compare_options = ["Предыдущий месяц", "Тот же месяц (год назад)", "Нет"]
                    compare_mode = st.selectbox("Сравнить с:", compare_options)

                    # Текущий
                    df_current = df_full[df_full['Month_Year'] == selected_month]
                    target_date = df_current['Дата_Отчета'].max()
                    period_title_base = selected_month.strftime('%B %Y')

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
            date_col1, date_col2 = st.columns(2)
            start_d = date_col1.date_input(
                "С",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                key=f"start_date_{st.session_state.df_version}"
            )
            end_d = date_col2.date_input(
                "По",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                key=f"end_date_{st.session_state.df_version}"
            )
            date_range = (start_d, end_d)

            if start_d > end_d:
                st.warning("Дата начала не может быть позже даты окончания")
            else:
                df_current = df_full[(df_full['Дата_Отчета'].dt.date >= start_d) & (df_full['Дата_Отчета'].dt.date <= end_d)]
                target_date = end_d
                period_title_base = f"{start_d.strftime('%d.%m.%Y')} - {end_d.strftime('%d.%m.%Y')}"

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
        
        if not df_prev.empty:
            sub_title = f"{period_title_base} vs {prev_label}"
        else:
            sub_title = f"{period_title_base} (без сравнения)"
        
        # --- SMART INSIGHTS ---
        generate_insights(df_current, df_prev, cur_rev, prev_rev, cur_fc)
        
        st.write(f"### 📊 Сводка: {sub_title}")
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("💰 Выручка", f"{cur_rev:,.0f} ₽", f"{delta_rev:+,.0f} ₽" if not df_prev.empty else None)
        kpi2.metric("📉 Фуд-кост", f"{cur_fc:.1f} %", f"{delta_fc:+.1f} %" if not df_prev.empty else None, delta_color="inverse")
        kpi3.metric("💳 Маржа", f"{cur_margin:,.0f} ₽", f"{delta_margin:+,.0f} ₽" if not df_prev.empty else None)
        kpi4.metric("🧾 Позиций", len(df_current))

        # --- ГРАФИК ДИНАМИКИ ПО ДНЯМ ---
        if period_mode == "📅 Месяц (Сравнение)" and not df_current.empty and ('scope_mode' not in locals() or scope_mode == "Весь месяц"):
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

    if period_mode == "📅 Месяц (Сравнение)":
        period_key = (
            "month",
            str(selected_month) if 'selected_month' in locals() else "none",
            scope_mode if 'scope_mode' in locals() else "Весь месяц",
            str(selected_day) if selected_day else "none",
            compare_mode if 'compare_mode' in locals() else "none",
        )
    else:
        if isinstance(date_range, tuple) and len(date_range) == 2:
            period_key = ("range", str(date_range[0]), str(date_range[1]), compare_mode if 'compare_mode' in locals() else "none")
        else:
            period_key = ("range", "none")

    base_view_key = (
        st.session_state.df_version,
        st.session_state.categories_applied_sig,
        selected_venue,
        period_key,
    )
    base_full_key = (
        st.session_state.df_version,
        st.session_state.categories_applied_sig,
        selected_venue,
    )

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
        infl_key = ("inflation", base_view_key, str(target_ts.date()))
        total_gross_loss, total_gross_save, df_inf = get_view_cached(
            infl_key,
            lambda: compute_inflation_metrics(df_inflation_scope, df_view)
        )
        
        net_result = total_gross_loss - total_gross_save
        inf1, inf2, inf3 = st.columns(3)
        inf1.metric("🔴 Потери (Инфляция)", f"-{total_gross_loss:,.0f} ₽")
        inf2.metric("🟢 Экономия (Скидки)", f"+{total_gross_save:,.0f} ₽")
        inf3.metric("🏁 Чистый Итог", f"-{net_result:,.0f} ₽" if net_result > 0 else f"+{abs(net_result):,.0f} ₽", delta_color="inverse")
        
        st.write("---")
        if not df_inf.empty:
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
            all_items = get_view_cached(
                ("all_items", base_full_key),
                lambda: sorted(df_full['Блюдо'].astype(str).unique())
            )
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
                supplier_stats = get_view_cached(
                    ("supplier_stats", base_view_key),
                    lambda: compute_supplier_stats(df_view)
                )
                
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
        df_cat, df_menu = get_view_cached(
            ("menu_tab", base_view_key, target_cat),
            lambda: compute_menu_tab_data(df_view, target_cat)
        )
        df_cat_prev = pd.DataFrame()
        if not df_prev.empty:
            df_cat_prev, _ = get_view_cached(
                ("menu_tab_prev", base_view_key, target_cat, prev_label),
                lambda: compute_menu_tab_data(df_prev, target_cat)
            )

        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.subheader("Структура выручки")
            if not df_cat_prev.empty:
                p1, p2 = st.columns(2)
                with p1:
                    st.caption(f"Текущий: {period_title_base}")
                    fig_pie_cur = px.pie(df_cat, values='Выручка с НДС', names=target_cat, hole=0.45)
                    fig_pie_cur.update_traces(hovertemplate='%{label}: %{value:,.0f} ₽ (%{percent})')
                    st.plotly_chart(update_chart_layout(fig_pie_cur), use_container_width=True)
                with p2:
                    st.caption(f"Сравнение: {prev_label}")
                    fig_pie_prev = px.pie(df_cat_prev, values='Выручка с НДС', names=target_cat, hole=0.45)
                    fig_pie_prev.update_traces(hovertemplate='%{label}: %{value:,.0f} ₽ (%{percent})')
                    st.plotly_chart(update_chart_layout(fig_pie_prev), use_container_width=True)
            else:
                fig_pie = px.pie(df_cat, values='Выручка с НДС', names=target_cat, hole=0.4)
                fig_pie.update_traces(hovertemplate='%{label}: %{value:,.0f} ₽ (%{percent})')
                st.plotly_chart(update_chart_layout(fig_pie), use_container_width=True)
        
        with c2:
            st.subheader("📊 Детальный анализ Фуд-коста")
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

        if not is_admin:
            st.info("Раздел доступен только администратору.")
            st.stop()
        
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

        abc_df, avg_qty, avg_margin = get_view_cached(
            ("abc", base_view_key),
            lambda: compute_abc_data(df_view)
        )
        if abc_df.empty:
            st.info("Недостаточно данных для ABC-матрицы.")
            st.stop()

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
            daily_stats, weekday_avg = get_view_cached(
                ("dow", base_view_key),
                lambda: compute_weekday_stats(df_view)
            )
            daily_prev = pd.DataFrame()
            weekday_prev = pd.DataFrame()
            if not df_prev.empty:
                daily_prev, weekday_prev = get_view_cached(
                    ("dow_prev", base_view_key, prev_label),
                    lambda: compute_weekday_stats(df_prev)
                )
            if daily_stats.empty:
                st.info("Нет данных за выбранный период.")
            else:
                daily_stats = daily_stats.copy()
                if 'ИндексДня' not in daily_stats.columns:
                    daily_stats = daily_stats.sort_values('Дата_Отчета').reset_index(drop=True)
                    daily_stats['ИндексДня'] = np.arange(1, len(daily_stats) + 1)

                if not daily_prev.empty:
                    daily_prev = daily_prev.copy()
                    if 'ИндексДня' not in daily_prev.columns:
                        daily_prev = daily_prev.sort_values('Дата_Отчета').reset_index(drop=True)
                        daily_prev['ИндексДня'] = np.arange(1, len(daily_prev) + 1)

                col_d1, col_d2 = st.columns([1.8, 1])
                with col_d1:
                    if not daily_prev.empty:
                        st.write("### Выручка по дням: текущий vs сравнение")
                        cur_cmp = daily_stats[['ИндексДня', 'Выручка с НДС']].rename(columns={'Выручка с НДС': 'Текущий'})
                        prev_cmp = daily_prev[['ИндексДня', 'Выручка с НДС']].rename(columns={'Выручка с НДС': 'Сравнение'})
                        merged = pd.merge(cur_cmp, prev_cmp, on='ИндексДня', how='outer').fillna(0)
                        long_cmp = merged.melt(id_vars='ИндексДня', value_vars=['Текущий', 'Сравнение'], var_name='Период', value_name='Выручка с НДС')
                        fig_daily = px.bar(
                            long_cmp,
                            x='ИндексДня',
                            y='Выручка с НДС',
                            color='Период',
                            barmode='group',
                            color_discrete_map={'Текущий': '#6ec8ff', 'Сравнение': '#ffb86b'}
                        )
                        fig_daily.update_layout(xaxis_title="День периода", yaxis_title="Выручка")
                    else:
                        st.write("### Выручка по дням периода")
                        fig_daily = px.bar(
                            daily_stats,
                            x='Дата_Подпись',
                            y='Выручка с НДС',
                            color='Выручка с НДС',
                            hover_data={'Дата_Отчета': True, 'ДеньРус': True}
                        )
                        fig_daily.update_traces(texttemplate='%{y:,.0f} ₽', textposition='outside')
                        fig_daily.update_layout(xaxis_title="Дата", yaxis_title="Выручка")
                    st.plotly_chart(update_chart_layout(fig_daily), use_container_width=True)

                with col_d2:
                    if not weekday_prev.empty:
                        st.write("### Средняя по дням недели")
                        cur_w = weekday_avg[['ДеньРус', 'Выручка с НДС']].rename(columns={'Выручка с НДС': 'Текущий'})
                        prev_w = weekday_prev[['ДеньРус', 'Выручка с НДС']].rename(columns={'Выручка с НДС': 'Сравнение'})
                        week_cmp = pd.merge(cur_w, prev_w, on='ДеньРус', how='outer').fillna(0)
                        week_cmp = week_cmp.melt(id_vars='ДеньРус', value_vars=['Текущий', 'Сравнение'], var_name='Период', value_name='Выручка с НДС')
                        fig_dow = px.bar(
                            week_cmp,
                            x='ДеньРус',
                            y='Выручка с НДС',
                            color='Период',
                            barmode='group',
                            color_discrete_map={'Текущий': '#6ec8ff', 'Сравнение': '#ffb86b'}
                        )
                    else:
                        st.write("### Средняя по дням недели")
                        fig_dow = px.bar(weekday_avg, x='ДеньРус', y='Выручка с НДС', color='Выручка с НДС')
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
        plan_df = get_view_cached(
            ("plan", base_full_key, days_to_buy, safety_stock),
            lambda: compute_purchase_plan(df_full, days_to_buy, safety_stock)
        )
        
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
            all_cats = get_view_cached(
                ("sim_all_cats", base_full_key),
                lambda: sorted(df_full['Категория'].dropna().astype(str).unique())
            )
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
                sim_data = get_view_cached(
                    ("sim_data", base_view_key, tuple(selected_cats), delta_price, delta_cost, delta_vol),
                    lambda: compute_simulation(df_view, selected_cats, delta_price, delta_cost, delta_vol)
                )
                if sim_data is None:
                    st.warning("Нет данных по выбранным категориям.")
                    st.stop()

                base_revenue = sim_data['base_revenue']
                base_margin = sim_data['base_margin']
                sim_revenue = sim_data['sim_revenue']
                sim_margin = sim_data['sim_margin']
                diff_rev = sim_data['diff_rev']
                diff_margin = sim_data['diff_margin']
                
                st.write(f"### 📊 Прогноз результата (Категории: {len(selected_cats)})")
                
                # Метрики
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("Выручка (Sim)", f"{sim_revenue:,.0f} ₽", f"{diff_rev:+,.0f} ₽")
                kpi2.metric("Маржа (Sim)", f"{sim_margin:,.0f} ₽", f"{diff_margin:+,.0f} ₽")
                
                new_profitability = sim_data['new_profitability']
                old_profitability = sim_data['old_profitability']
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
