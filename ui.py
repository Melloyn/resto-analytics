import streamlit as st
import streamlit.components.v1 as components
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, ColumnsAutoSizeMode, JsCode

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
            /* Ultra-clear glass sidebar */
            background: linear-gradient(165deg, rgba(160, 200, 255, 0.05), rgba(100, 160, 255, 0.02)) !important;
            backdrop-filter: blur(24px) saturate(140%);
            -webkit-backdrop-filter: blur(24px) saturate(140%);
            border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
            box-shadow: 
                inset -1px 0 2px rgba(255, 255, 255, 0.2), 
                15px 0 40px rgba(0, 5, 15, 0.4);
        }

        [data-testid="stSidebar"] * {
            color: var(--text-main) !important;
        }

        [data-testid="stMetric"],
        [data-testid="stVerticalBlock"] > [data-testid="element-container"] > div:has([data-testid="stDataFrame"]) {
            /* Remove simple border, replace with complex box-shadow for 3D liquid edge */
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.25) !important;
            border-bottom: 1px solid rgba(0, 0, 0, 0.2) !important;
            animation: glassFadeUp var(--anim-mid) var(--ease-fluid);
        }

        [data-testid="stMetric"] {
            position: relative;
            overflow: hidden;
            background: linear-gradient(155deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.01)) !important;
            backdrop-filter: blur(25px) saturate(130%);
            -webkit-backdrop-filter: blur(25px) saturate(130%);
            padding: 15px !important;
            border-radius: 20px !important;
            box-shadow: 
                inset 0 1px 1px rgba(255, 255, 255, 0.4),   /* Top highlight */
                inset 0 -1px 2px rgba(255, 255, 255, 0.05), /* Bottom soft highlight */
                0 8px 24px rgba(0, 0, 0, 0.25) !important;  /* Soft deep shadow */
            transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
        }

        [data-testid="stMetric"]::after {
            content: "";
            position: absolute;
            inset: 0;
            border-radius: inherit;
            /* Enhance the diagonal liquid shine */
            background: linear-gradient(125deg, rgba(255, 255, 255, 0.35) 0%, rgba(255, 255, 255, 0.0) 30%, rgba(255, 255, 255, 0.0) 70%, rgba(255, 255, 255, 0.05) 100%);
            pointer-events: none;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-3px) scale(1.01);
            border-top: 1px solid rgba(255, 255, 255, 0.4) !important;
            box-shadow: 
                inset 0 2px 3px rgba(255, 255, 255, 0.5),
                inset 0 -2px 5px rgba(255, 255, 255, 0.1),
                0 15px 35px rgba(0, 0, 0, 0.35),
                0 10px 20px rgba(115, 195, 255, 0.1) !important; /* Soft blue glow on hover */
            background: linear-gradient(160deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.02)) !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.6) !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 26px;
            font-weight: 700;
            color: #ffffff;
            text-shadow: 0 2px 10px rgba(255, 255, 255, 0.2);
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
            /* Glassy container for expanders */
            background: linear-gradient(160deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.01)) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.25) !important;
            border-bottom: 1px solid rgba(0, 0, 0, 0.3) !important;
            border-radius: 18px !important;
            backdrop-filter: blur(20px) saturate(130%);
            -webkit-backdrop-filter: blur(20px) saturate(130%);
            box-shadow: 
                inset 0 1px 1px rgba(255, 255, 255, 0.3),
                0 10px 32px rgba(0, 10, 30, 0.3);
            animation: glassFadeUp var(--anim-mid) var(--ease-fluid);
            transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
            overflow: hidden !important;
        }

        [data-testid="stExpander"]:hover {
            border-top: 1px solid rgba(255, 255, 255, 0.4) !important;
            box-shadow: 
                inset 0 1px 2px rgba(255, 255, 255, 0.4),
                0 15px 40px rgba(0, 10, 30, 0.4);
            transform: translateY(-2px);
        }

        [data-testid="stExpander"] details {
            border-radius: 18px !important;
            overflow: hidden !important;
            background: transparent !important;
        }

        [data-testid="stExpander"] summary {
            border-radius: 16px !important;
            border: none !important;
            background: transparent !important;
            padding: 10px 15px !important;
        }

        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
            background: linear-gradient(175deg, rgba(0, 0, 0, 0.1), rgba(0, 0, 0, 0.2)) !important;
            border-top: 1px solid rgba(0, 0, 0, 0.3);
            border-radius: 0 0 16px 16px !important;
            box-shadow: inset 0 5px 10px rgba(0,0,0,0.1);
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
            /* Glowing primary button */
            background: linear-gradient(135deg, rgba(80, 170, 255, 0.7) 0%, rgba(30, 90, 200, 0.8) 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-bottom: 1px solid rgba(0, 0, 0, 0.4) !important;
            border-radius: 999px !important; /* Pill shape */
            box-shadow: 
                inset 0 2px 5px rgba(255, 255, 255, 0.5),
                inset 0 -4px 8px rgba(0, 0, 0, 0.3),
                0 8px 18px rgba(30, 100, 220, 0.4) !important; /* Colored soft drop shadow */
            transition: all 0.35s cubic-bezier(0.25, 1, 0.35, 1) !important;
            font-weight: 700;
            text-shadow: 0 1px 3px rgba(0,0,0,0.4);
            backdrop-filter: blur(20px) saturate(140%);
            -webkit-backdrop-filter: blur(20px) saturate(140%);
        }

        button[kind="primary"]:hover {
            transform: translateY(-2px) scale(1.02);
            filter: brightness(1.15);
            box-shadow: 
                inset 0 2px 6px rgba(255, 255, 255, 0.7),
                inset 0 -4px 8px rgba(0, 0, 0, 0.3),
                0 14px 28px rgba(30, 100, 220, 0.6) !important; /* Stronger colored glow */
        }

        button[kind="secondary"] {
            /* Clear glass secondary button */
            background: linear-gradient(150deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.02)) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-bottom: 1px solid rgba(0, 0, 0, 0.2) !important;
            border-radius: 999px !important; /* Pill shape */
            color: rgba(255, 255, 255, 0.8) !important;
            backdrop-filter: blur(15px) saturate(120%);
            -webkit-backdrop-filter: blur(15px) saturate(120%);
            box-shadow: 
                inset 0 1px 2px rgba(255, 255, 255, 0.3),
                inset 0 -1px 2px rgba(0, 0, 0, 0.1),
                0 5px 12px rgba(0, 5, 15, 0.2) !important; /* Deep drop shadow */
            transition: all 0.3s cubic-bezier(0.25, 1, 0.35, 1) !important;
            font-weight: 600;
        }

        button[kind="secondary"]:hover {
            background: linear-gradient(150deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.05)) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.5) !important;
            color: #ffffff !important;
            transform: translateY(-2px);
            box-shadow: 
                inset 0 1px 3px rgba(255, 255, 255, 0.5),
                inset 0 -1px 2px rgba(0, 0, 0, 0.1),
                0 10px 20px rgba(0, 5, 20, 0.3) !important;
        }

        .stSelectbox label, .stRadio label, .stDateInput label, .stTextInput label, .stNumberInput label {
            font-weight: 500 !important;
            color: rgba(255, 255, 255, 0.6) !important;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
            margin-bottom: 0.5rem !important;
            font-size: 13px !important;
        }

        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div,
        [data-baseweb="base-input"] > input,
        [data-baseweb="input"] > input {
            /* Pill-shaped deeply recessed glass inputs with bottom neon glow */
            /* Background is very dark to contrast with the glow */
            background: linear-gradient(180deg, rgba(15, 25, 45, 0.4) 0%, rgba(20, 35, 65, 0.2) 100%) !important;
            
            /* The borders create the "glass edge" effect */
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-top: 1px solid rgba(0, 0, 0, 0.8) !important;       /* Deep shadow at top inside edge */
            border-bottom: 1px solid rgba(130, 200, 255, 0.4) !important; /* The signature neon blue line at the bottom */
            
            border-radius: 8px !important; /* Slightly rounded rectangle, not full pill for inputs in refernce */
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            color: #ffffff !important;
            
            /* Inner shadow for depth, and soft outer glow from the blue bottom line */
            box-shadow: 
                inset 0 6px 10px rgba(0, 0, 0, 0.6),                  /* Deep inner top shadow */
                inset 0 -2px 5px rgba(100, 180, 255, 0.15),           /* Inner blue reflection */
                0 4px 12px rgba(0, 0, 0, 0.5),                        /* Drop shadow */
                0 4px 15px -4px rgba(80, 170, 255, 0.2) !important;     /* Neon glow bleeding down */
            
            transition: all 0.3s cubic-bezier(0.25, 1, 0.35, 1);
            min-height: 42px !important;
        }

        [data-baseweb="select"] > div:hover,
        [data-baseweb="input"] > div:hover,
        [data-baseweb="base-input"] > input:hover {
            border-bottom: 1px solid rgba(150, 220, 255, 0.6) !important; /* Brighter bottom line on hover */
            background: linear-gradient(180deg, rgba(20, 30, 55, 0.5) 0%, rgba(30, 45, 80, 0.3) 100%) !important;
            box-shadow: 
                inset 0 6px 12px rgba(0, 0, 0, 0.7),
                inset 0 -3px 8px rgba(100, 180, 255, 0.25),
                0 6px 14px rgba(0, 0, 0, 0.6),
                0 6px 20px -3px rgba(80, 170, 255, 0.4) !important; /* Stronger neon glow */
        }

        [data-baseweb="select"] > div:focus-within,
        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="base-input"] > input:focus {
            /* Active/Focus state gets brighter full border and stronger glow */
            border: 1px solid rgba(100, 180, 255, 0.5) !important;
            border-bottom: 1px solid rgba(150, 220, 255, 0.9) !important;
            box-shadow: 
                inset 0 4px 8px rgba(0, 0, 0, 0.5),
                inset 0 -2px 10px rgba(100, 180, 255, 0.3),
                0 0 20px rgba(100, 180, 255, 0.35) !important; /* Full outer neon glow */
        }

        /* Adjust icon and placeholder colors inside inputs */
        [data-baseweb="select"] span, [data-baseweb="input"] ::placeholder {
            color: rgba(255, 255, 255, 0.4) !important;
        }

        /* --- TABS GLASSMORPHISM REDESIGN --- */
        div[data-testid="stTabs"] {
            margin-top: 1rem;
        }
        
        div[data-testid="stTabs"] > div[data-baseweb="tab-list"] {
            gap: 16px;
            background: transparent;
            padding-bottom: 25px; /* space for soft colored glow shadows */
            padding-top: 5px;
            overflow: visible !important;
        }
        
        div[data-testid="stTabs"] > div[data-baseweb="tab-list"] div[data-testid="stTabActiveIndicator"] {
            display: none !important; /* Hide default ugly solid line */
        }
        
        div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button[data-baseweb="tab"] {
            /* Clear dark glassy base for inactive */
            background: linear-gradient(180deg, rgba(30, 45, 75, 0.4) 0%, rgba(15, 25, 45, 0.6) 100%) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-bottom: 2px solid rgba(0, 0, 0, 0.4) !important;
            border-radius: 8px !important; /* Retained from the reference image */
            padding: 10px 26px !important;
            color: rgba(255, 255, 255, 0.5) !important;
            font-weight: 600 !important;
            font-size: 15px !important;
            height: auto !important;
            margin: 0 !important;
            box-shadow: 
                inset 0 1px 1px rgba(255, 255, 255, 0.1),   /* sharp upper inner edge */
                inset 0 -1px 2px rgba(255, 255, 255, 0.05),  /* soft lower inner edge */
                0 4px 15px rgba(0, 0, 0, 0.4) !important;   /* standard drop shadow */
            transition: all 0.35s cubic-bezier(0.25, 1, 0.35, 1) !important;
            backdrop-filter: blur(20px) saturate(120%);
            -webkit-backdrop-filter: blur(20px) saturate(120%);
            overflow: visible !important;
        }

        div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button[data-baseweb="tab"]:focus {
            outline: none !important;
        }

        div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button[data-baseweb="tab"]:hover {
            color: rgba(255, 255, 255, 0.8) !important;
            background: linear-gradient(180deg, rgba(35, 50, 85, 0.5) 0%, rgba(20, 30, 55, 0.7) 100%) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.25) !important;
            transform: translateY(-2px);
            box-shadow: 
                inset 0 1px 2px rgba(255, 255, 255, 0.2),
                inset 0 -2px 3px rgba(255, 255, 255, 0.05),
                0 8px 20px rgba(0, 0, 0, 0.5) !important;
        }
        
        div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button[data-baseweb="tab"][aria-selected="true"] {
            /* Active glowing glowing inner shadow look */
            background: linear-gradient(180deg, rgba(20, 40, 80, 0.6) 0%, rgba(10, 20, 50, 0.4) 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-bottom: 2px solid rgba(130, 200, 255, 0.9) !important; /* Thick glowing base */
            box-shadow: 
                inset 0 1px 1px rgba(255, 255, 255, 0.2),    /* Top edge */
                inset 0 -5px 15px rgba(100, 180, 255, 0.4),  /* Inner glowing blue from bottom */
                0 6px 15px rgba(0, 0, 0, 0.5),                 /* Outer dark shadow */
                0 8px 25px -4px rgba(80, 170, 255, 0.6) !important; /* Intense outer bright glow */
            transform: translateY(-2px);
            /* Make it feel like colored glass */
            backdrop-filter: blur(25px) saturate(160%);
            -webkit-backdrop-filter: blur(25px) saturate(160%);
        }
        
        div[data-testid="stTabs"] > div[data-baseweb="tab-panel"] {
            outline: none !important;
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
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
            box-shadow: none !important;
            border-bottom: none !important;
        }
        [data-testid="stToolbar"] {
            display: flex !important;
        }
        [data-testid="stDecoration"] {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            z-index: 1001 !important;
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
        /* --- SKELETON UI --- */
        @keyframes skeletonPulse {
            0% { opacity: 0.6; filter: brightness(1); }
            50% { opacity: 0.3; filter: brightness(0.8); }
            100% { opacity: 0.6; filter: brightness(1); }
        }

        .skeleton-box {
            animation: skeletonPulse 1.8s ease-in-out infinite;
            background: linear-gradient(160deg, rgba(30, 45, 75, 0.4) 0%, rgba(15, 25, 45, 0.6) 100%) !important;
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-top: 1px solid rgba(255, 255, 255, 0.15);
            border-bottom: 2px solid rgba(130, 200, 255, 0.2);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 1rem;
            box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.1), 0 4px 15px rgba(0, 0, 0, 0.4);
            height: 100%;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            overflow: hidden;
            position: relative;
        }

        .skeleton-box::after {
            content: "";
            position: absolute;
            top: 0; left: -100%; width: 50%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.08), transparent);
            animation: skeletonSweep 2s infinite;
        }

        @keyframes skeletonSweep {
            100% { left: 200%; }
        }

        .skeleton-line {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            height: 14px;
            margin-bottom: 12px;
        }

        .skeleton-title { width: 50%; height: 12px; margin-bottom: 20px; }
        .skeleton-value { width: 70%; height: 32px; border-radius: 12px; margin-bottom: 15px; background: rgba(255, 255, 255, 0.15); }
        .skeleton-delta { width: 40%; height: 12px; }

        .skeleton-chart {
            min-height: 350px;
            justify-content: flex-end;
        }
        
    </style>
    """, unsafe_allow_html=True)

    # Global glassmorphism override theme (requested full UI restyle).
    st.markdown("""
    <style>
        :root{
            --ra-bg: #0B0E14;
            --ra-glass: rgba(255,255,255,0.03);
            --ra-text: #E0E0E0;
            --ra-accent: #70D7FF;
            --ra-accent-2: #9D50BB;
            --ra-good: #50FFBB;
            --ra-bad: #FF5050;
            --ra-border-grad: linear-gradient(145deg, rgba(255,255,255,0.42), rgba(255,255,255,0.18) 28%, rgba(255,255,255,0.0) 70%);
            --ra-shadow-outer: 0 8px 32px 0 rgba(0,0,0,0.6);
            --ra-shadow-inner: inset 0 0 12px rgba(255,255,255,0.1);
            --ra-glow: 0 0 18px rgba(112,215,255,0.24);
            --ra-ease: cubic-bezier(0.4, 0, 0.2, 1);
        }

        html, body, .stApp{
            background: var(--ra-bg) !important;
            color: var(--ra-text) !important;
        }

        .main .block-container{
            padding-top: 2.2rem !important;
            padding-bottom: 2.6rem !important;
            max-width: 96% !important;
        }

        h1, h2, h3{
            letter-spacing: 0.04em !important;
            color: #f4f8ff !important;
        }

        /* Shared glass surface */
        [data-testid="stMetric"],
        [data-testid="stExpander"],
        [data-testid="stDataFrame"],
        [data-testid="stAlert"],
        [role="tab"],
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        button[kind],
        .ag-root-wrapper,
        .stTextInput > div > div,
        .stNumberInput > div > div,
        .stDateInput > div > div {
            position: relative !important;
            overflow: hidden !important;
            background: var(--ra-glass) !important;
            backdrop-filter: blur(40px) saturate(135%) !important;
            -webkit-backdrop-filter: blur(40px) saturate(135%) !important;
            border: 1px solid rgba(180, 220, 255, 0.25) !important;
            box-shadow: var(--ra-shadow-outer), var(--ra-shadow-inner), var(--ra-glow) !important;
            transition: all 0.4s var(--ra-ease) !important;
        }

        /* shimmer */
        button[kind] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div{
            background-clip: padding-box !important;
        }
        button[kind]:hover,
        button[kind]:focus-visible,
        [data-testid="stMetric"]:hover,
        [data-testid="stExpander"]:hover,
        [role="tab"]:hover,
        div[data-baseweb="input"] > div:hover,
        div[data-baseweb="input"] > div:focus-within,
        div[data-baseweb="select"] > div:hover,
        div[data-baseweb="select"] > div:focus-within{
            transform: translateY(-2px) !important;
            box-shadow:
                0 10px 36px rgba(0,0,0,0.68),
                inset 0 0 14px rgba(255,255,255,0.18),
                0 0 22px rgba(112,215,255,0.46),
                0 0 28px rgba(157,80,187,0.24) !important;
        }
        button[kind]::selection{ background: transparent; }
        @keyframes raShimmer{
            0%{ background: linear-gradient(45deg, transparent, rgba(255,255,255,0.0), transparent); }
            35%{ background: linear-gradient(45deg, transparent, rgba(255,255,255,0.17), transparent); }
            100%{ background: linear-gradient(45deg, transparent, rgba(255,255,255,0.0), transparent); }
        }

        /* Buttons */
        button[kind]{
            border-radius: 16px !important;
            color: #edf6ff !important;
            letter-spacing: 0.03em !important;
            padding: 0.62rem 1rem !important;
        }
        button[kind="primary"]{
            box-shadow:
                0 8px 32px rgba(0,0,0,0.65),
                inset 0 0 12px rgba(255,255,255,0.12),
                0 0 24px rgba(112,215,255,0.52) !important;
        }

        /* Active tabs / toggles */
        [role="tab"][aria-selected="true"]{
            border-color: rgba(112,215,255,0.9) !important;
            box-shadow:
                0 10px 32px rgba(0,0,0,0.64),
                inset 0 0 14px rgba(255,255,255,0.2),
                0 0 26px rgba(112,215,255,0.6),
                0 0 30px rgba(157,80,187,0.45) !important;
        }
        [role="tablist"],
        div[data-baseweb="tab-list"]{
            overflow: visible !important;
            padding-top: 6px !important;
        }
        [role="tab"]{
            overflow: visible !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"]{
            background: rgba(255,255,255,0.03) !important;
            backdrop-filter: blur(40px) !important;
            -webkit-backdrop-filter: blur(40px) !important;
            border-right: 1px solid rgba(255,255,255,0.2) !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.6), inset 0 0 12px rgba(255,255,255,0.1) !important;
        }

        /* Tables: keep contrast stable (fix washed-out data) */
        .ag-theme-streamlit,
        .ag-theme-alpine,
        .ag-root-wrapper{
            --ag-background-color: rgba(11, 20, 35, 0.9) !important;
            --ag-foreground-color: #eaf3ff !important;
            --ag-header-background-color: rgba(24, 42, 70, 0.92) !important;
            --ag-header-foreground-color: #f3f8ff !important;
            --ag-odd-row-background-color: rgba(24, 40, 64, 0.34) !important;
            --ag-row-hover-color: rgba(46, 77, 120, 0.45) !important;
            --ag-row-border-color: rgba(160, 205, 255, 0.12) !important;
            --ag-border-color: rgba(180, 220, 255, 0.25) !important;
            border-radius: 16px !important;
            background: linear-gradient(160deg, rgba(26, 44, 74, 0.42), rgba(13, 24, 43, 0.5)) !important;
            backdrop-filter: blur(22px) saturate(130%) !important;
            -webkit-backdrop-filter: blur(22px) saturate(130%) !important;
            border: 1px solid rgba(180, 220, 255, 0.25) !important;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45), inset 0 0 14px rgba(255, 255, 255, 0.07) !important;
            color: #eaf3ff !important;
        }
        .ag-header{
            background: linear-gradient(180deg, rgba(38, 62, 96, 0.68), rgba(22, 37, 61, 0.7)) !important;
            border-bottom: 1px solid rgba(143, 205, 255, 0.28) !important;
        }
        .ag-header-cell-label, .ag-header-cell-text{
            color: #f3f8ff !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em !important;
        }
        .ag-row{
            background: rgba(15, 27, 45, 0.88) !important;
            border-bottom: 1px solid rgba(160, 205, 255, 0.12) !important;
            box-shadow: none !important;
        }
        .ag-row-odd{
            background: rgba(15, 27, 45, 0.88) !important;
        }
        .ag-row-even{
            background: rgba(12, 23, 39, 0.88) !important;
        }
        .ag-row:nth-child(even){
            background: rgba(12, 23, 39, 0.88) !important;
        }
        .ag-row-hover{
            background: rgba(46, 77, 120, 0.45) !important;
            box-shadow: inset 0 0 0 1px rgba(123, 201, 255, 0.25) !important;
        }
        .ag-cell{
            color: #eaf3ff !important;
            background: inherit !important;
            border-right: 1px solid rgba(145, 188, 240, 0.12) !important;
        }
        .ag-ltr .ag-cell:last-child{
            border-right: none !important;
        }
        .ag-header-cell{
            border-right: 1px solid rgba(145, 188, 240, 0.16) !important;
        }
        .ag-header-cell:last-child{
            border-right: none !important;
        }
        .ag-root-wrapper-body.ag-layout-normal{
            background: transparent !important;
        }
        .ag-center-cols-clipper,
        .ag-center-cols-container,
        .ag-body-viewport,
        .ag-body-horizontal-scroll-viewport{
            background: rgba(11, 20, 35, 0.96) !important;
        }
        .ag-body-viewport::-webkit-scrollbar,
        .ag-body-horizontal-scroll-viewport::-webkit-scrollbar{
            width: 10px;
            height: 10px;
        }
        .ag-body-viewport::-webkit-scrollbar-thumb,
        .ag-body-horizontal-scroll-viewport::-webkit-scrollbar-thumb{
            background: rgba(120, 190, 255, 0.32);
            border-radius: 999px;
        }

        /* negative pulse for critical cards if down icon exists */
        [data-testid="stMetric"]:has([data-testid="stMetricDelta"] svg[aria-label*="down"]),
        [data-testid="stMetric"]:has([data-testid="stMetricDelta"] svg[aria-label*="Down"]){
            animation: raPulseBad 1.5s infinite alternate;
        }
        @keyframes raPulseBad{
            from{ box-shadow: 0 8px 32px rgba(0,0,0,0.6), inset 0 0 12px rgba(255,255,255,0.1), 0 0 10px rgba(255,80,80,0.35); }
            to{ box-shadow: 0 8px 32px rgba(0,0,0,0.6), inset 0 0 12px rgba(255,255,255,0.1), 0 0 20px rgba(255,80,80,0.7); }
        }

        /* alerts and insight blocks */
        [data-testid="stAlert"]{
            border-radius: 16px !important;
            margin-top: 0.65rem !important;
            margin-bottom: 0.65rem !important;
        }

        /* spacing */
        [data-testid="stVerticalBlock"] > [data-testid="element-container"]{
            margin-bottom: 0.75rem !important;
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

def render_aggrid(df, height=400, pagination=False, formatting=None, fit_columns=False, theme="balham"):
    if df.empty:
        st.info("Нет данных для отображения")
        return
        
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # Enable filtering and sorting for all columns
    gb.configure_default_column(filterable=True, sortable=True, resizable=True, wrapText=True, autoHeight=True)
    
    import pandas as pd
    
    for col in df.columns:
        is_num = pd.api.types.is_numeric_dtype(df[col])
        flex_val = 1 if is_num else 3
        min_w = 80 if is_num else 150
        max_w = {"maxWidth": 120} if is_num else {}
        
        col_kwargs = {"minWidth": min_w, "flex": flex_val, **max_w}
        
        if formatting and col in formatting:
            fmt = formatting[col]
            if fmt.startswith("%.") and ("f" in fmt or "%%" in fmt):
                # Basic numeric formatting helper for AgGrid
                js_fmt = f"val.toLocaleString('ru-RU', {{minimumFractionDigits: {fmt[2]}, maximumFractionDigits: {fmt[2]}}})"
                if "%%" in fmt:
                     js_fmt = f"({js_fmt} + ' %')"
                elif "₽" in fmt:
                     js_fmt = f"({js_fmt} + ' ₽')"
                
                jscode_str = f"""function(params) {{
                    if (params.value == null || params.value === 'nan' || params.value === 'NaN') return '';
                    const val = Number(params.value);
                    if (isNaN(val)) return params.value;
                    return {js_fmt};
                }}"""
                gb.configure_column(col, valueFormatter=JsCode(jscode_str), **col_kwargs)
            else:
                 gb.configure_column(col, **col_kwargs)
        elif pd.api.types.is_numeric_dtype(df[col]):
            jscode_str = """function(params) {
                if (params.value == null || params.value === 'nan' || params.value === 'NaN') return '';
                const val = Number(params.value);
                if (isNaN(val)) return params.value;
                return val.toLocaleString('ru-RU', {minimumFractionDigits: 0, maximumFractionDigits: 2});
            }"""
            gb.configure_column(col, valueFormatter=JsCode(jscode_str), **col_kwargs)
        else:
             gb.configure_column(col, **col_kwargs)
    
    if pagination:
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)
        
    gb.configure_grid_options(wrapHeaderText=True, autoHeaderHeight=True)
    gridOptions = gb.build()
    
    # Safe fallback for themes
    valid_themes = ["streamlit", "alpine", "balham", "material"]
    safe_theme = theme if theme in valid_themes else "balham"

    # Using dark theme to match the rest of the app
    AgGrid(
        df,
        gridOptions=gridOptions,
        height=height,
        theme=safe_theme,
        custom_css={
            ".ag-theme-alpine, .ag-theme-balham": {
                "--ag-background-color": "rgba(11, 20, 35, 0.9)",
                "--ag-foreground-color": "#eaf3ff",
                "--ag-header-background-color": "rgba(24, 42, 70, 0.92)",
                "--ag-header-foreground-color": "#f3f8ff",
                "--ag-odd-row-background-color": "rgba(15, 27, 45, 0.88)",
                "--ag-row-hover-color": "rgba(46, 77, 120, 0.45)",
                "--ag-row-border-color": "rgba(160, 205, 255, 0.12)",
                "--ag-border-color": "rgba(180, 220, 255, 0.25)",
            },
            ".ag-root-wrapper": {
                "border-radius": "14px",
                "overflow": "hidden",
                "border": "1px solid rgba(180, 220, 255, 0.25)",
                "box-shadow": "0 12px 32px rgba(0, 0, 0, 0.45), inset 0 0 14px rgba(255,255,255,0.07)",
                "background": "linear-gradient(160deg, rgba(26, 44, 74, 0.42), rgba(13, 24, 43, 0.5)) !important",
            },
            ".ag-header": {
                "background": "linear-gradient(180deg, rgba(38, 62, 96, 0.68), rgba(22, 37, 61, 0.7)) !important",
                "border-bottom": "1px solid rgba(143, 205, 255, 0.28)"
            },
            ".ag-header-cell-label": {"color": "#f3f8ff !important", "font-weight": "600"},
            ".ag-row": {"background-color": "rgba(15, 27, 45, 0.88) !important", "color": "#eaf3ff !important"},
            ".ag-row-odd": {"background-color": "rgba(15, 27, 45, 0.88) !important", "color": "#eaf3ff !important"},
            ".ag-row-even": {"background-color": "rgba(12, 23, 39, 0.88) !important", "color": "#eaf3ff !important"},
            ".ag-row-hover": {"background-color": "rgba(46, 77, 120, 0.45) !important"},
            ".ag-cell": {"color": "#eaf3ff !important", "background-color": "inherit !important", "border-right": "1px solid rgba(145, 188, 240, 0.12)"},
            ".ag-center-cols-clipper": {"background-color": "rgba(11, 20, 35, 0.96) !important"},
            ".ag-center-cols-container": {"background-color": "rgba(11, 20, 35, 0.96) !important"},
            ".ag-body-viewport": {"background-color": "rgba(11, 20, 35, 0.96) !important"},
        },
        update_mode=GridUpdateMode.NO_UPDATE,
        allow_unsafe_jscode=True
    )

def render_skeleton_kpis(num_cols=3):
    """Отрисовывает анимированные плейсхолдеры для KPI карточек."""
    cols = st.columns(num_cols)
    for col in cols:
        with col:
            st.markdown(f'''
            <div class="skeleton-box">
                <div class="skeleton-title skeleton-line"></div>
                <div class="skeleton-value skeleton-line"></div>
                <div class="skeleton-delta skeleton-line"></div>
            </div>
            ''', unsafe_allow_html=True)

def render_skeleton_chart():
    """Отрисовывает анимированный плейсхолдер для большого графика."""
    st.markdown(f'''
    <div class="skeleton-box skeleton-chart">
        <div class="skeleton-title skeleton-line" style="width: 30%;"></div>
        <div style="display: flex; gap: 10px; height: 80%; align-items: flex-end;">
            <div class="skeleton-line" style="width: 10%; height: 30%;"></div>
            <div class="skeleton-line" style="width: 10%; height: 60%;"></div>
            <div class="skeleton-line" style="width: 10%; height: 80%;"></div>
            <div class="skeleton-line" style="width: 10%; height: 40%;"></div>
            <div class="skeleton-line" style="width: 10%; height: 90%;"></div>
            <div class="skeleton-line" style="width: 10%; height: 50%;"></div>
            <div class="skeleton-line" style="width: 10%; height: 75%;"></div>
            <div class="skeleton-line" style="width: 10%; height: 100%;"></div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
