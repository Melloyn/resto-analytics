import streamlit as st
import streamlit.components.v1 as components

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
