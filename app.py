import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import re
import json
import numpy as np
import os
import telegram_utils
from io import BytesIO
from datetime import datetime, timedelta

# --- CHART THEME ---
def update_chart_layout(fig):
    fig.update_layout(
        template="plotly_dark",
        font=dict(family="Inter", size=12),
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#333", zeroline=False),
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
        /* Import Inter Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
            border-right: 1px solid #333 !important;
        }

        /* Metric Cards */
        [data-testid="stMetric"] {
            background-color: #1E1E1E !important;
            padding: 15px !important;
            border-radius: 10px !important;
            border: 1px solid #333 !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 14px;
            color: #888;
        }

        [data-testid="stMetricValue"] {
            font-size: 24px;
            font-weight: 600;
            color: #FFF;
        }
        
        [data-testid="stMetricDelta"] {
            font-size: 14px;
        }

        /* Headers */
        h1, h2, h3 {
            font-weight: 600;
            letter-spacing: -0.5px;
        }
        
        /* Expander Styling */
        .streamlit-expanderHeader {
            background-color: #1E1E1E;
            border-radius: 5px;
        }

        /* Remove Deploy Button & Padding */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
    </style>
    """, unsafe_allow_html=True)

setup_style()

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

# --- 1. ГРУППИРОВКА ДЛЯ МАКРО-УРОВНЯ ---
def get_macro_category(cat):
    if cat in ['☕ Кофе', '🍵 Чай', '🍓 Милк/Фреш/Смузи', '🧉 Коктейль Б/А', '🚰 Розлив Б/А', '🥤 Стекло/Банка Б/А']: 
        return '☕ Безалкогольное'
    if cat in ['🍏 Сидр ШТ', '🍾 Пиво ШТ', '🍺 Пиво Розлив']: 
        return '🍺 Пиво/Сидр'
    if cat in ['🥃 Виски', '💧 Водка', '🏴‍☠️ Ром', '🌵 Текила', '🌲 Джин', '🍇 Коньяк/Бренди', '🍒 Ликер/Настойка']: 
        return '🥃 Крепкое'
    return cat

# --- 2. ГРАНУЛЯРНЫЙ КАТЕГОРИЗАТОР ---
def detect_category_granular(name_input):
    name = str(name_input).strip().lower()
    
    # ЖЕСТКАЯ БАЗА
    manual_dict = {
        'banana tiki': '🍹 Коктейли', 'black hole': '🍹 Коктейли', 'clover club': '🍹 Коктейли', 
        'drunk bee': '🍹 Коктейли', 'milk punch бурбон-черная смородина': '🍹 Коктейли', 
        'milk punch виски-вишня': '🥃 Виски', 'milk punch ром-кокос': '🍹 Коктейли', 
        'nevermind': '🍹 Коктейли', 'party-mix с виски': '🥃 Виски', 'passion star martini': '🍹 Коктейли', 
        'pineapple spritz dmf pineapple': '🍹 Коктейли', 'rum bubble': '🍹 Коктейли', 'zombieville': '🍹 Коктейли', 
        'авторское рислинг 125мл': '🍷 Вино', 'авторское совиньон блан 125мл': '🍷 Вино', 
        'авторское совиньон блан 750мл': '🍷 Вино', 'айриш кофе': '🍹 Коктейли', 'антико итальяно 125мл': '🍷 Вино', 
        'антико итальяно 700мл': '🍷 Вино', 'апельсин 20г': '🍬 Доп. ингредиенты', 'апероль шприц': '🍹 Коктейли', 
        'асканели 40мл': '🍇 Коньяк/Бренди', 'балантайнс 40мл': '🥃 Виски', 'бандидо 40мл': '🌵 Текила', 
        'белая березка 40мл': '💧 Водка', 'белуга нобл 40мл': '💧 Водка', 'белый русский': '🍹 Коктейли', 
        'берн 0,33': '🥤 Стекло/Банка Б/А', 'биттербулл': '🍹 Коктейли', 'блэк рэм 40 мл': '🥃 Виски', 
        'блэк шип 500мл': '🍺 Пиво Розлив', 'боржоми 0,5': '🥤 Стекло/Банка Б/А', 'брамбл': '🍹 Коктейли', 
        'брум в асс. 40мл': '🌲 Джин', 'вино местное 125мл': '🍷 Вино', 'вино местное ежевичное 125мл': '🍺 Пиво Розлив', 
        'виски кола': '🍹 Коктейли', 'вода с лимоном': '🚰 Розлив Б/А', 'гато негро 125мл': '🍷 Вино', 
        'гленливет 12 лет 40мл': '🥃 Виски', 'глинтвей б/а': '🧉 Коктейль Б/А', 'глинтвейн': '🍹 Коктейли', 
        'глинтвейн б/а бур': '🧉 Коктейль Б/А', 'глинтвейн белый': '🍹 Коктейли', 'глинтвейн белый б/а': '🧉 Коктейль Б/А', 
        'глинтвейн бур': '🍹 Коктейли', 'голубые гаваи': '🍹 Коктейли', 'грейпфрутовый фреш 250 мл': '🍓 Милк/Фреш/Смузи', 
        'дайкири в ассортименте': '🍹 Коктейли', 'джемесон 40мл': '🥃 Виски', 'джин-тоник': '🥤 Стекло/Банка Б/А', 
        'джин-тропик': '🍹 Коктейли', 'егермейстер 40мл': '🍒 Ликер/Настойка', 'иван чай 400мл бур': '🍵 Чай', 
        'капучино с кокосовым молоком': '☕ Кофе', 'капучино с миндальным молоком': '☕ Кофе', 'космополитен': '🍹 Коктейли', 
        'кофе американо 150 мл': '☕ Кофе', 'кофе американо бур': '☕ Кофе', 'кофе американо для персонала': '☕ Кофе', 
        'кофе двойной американо бур': '☕ Кофе', 'кофе двойной капучино бур': '☕ Кофе', 'кофе капучино': '☕ Кофе', 
        'кофе капучино для персонала': '☕ Кофе', 'кофе латте': '☕ Кофе', 'кофе латте бур': '☕ Кофе', 
        'кофе по восточном': '☕ Кофе', 'кофе со специями': '☕ Кофе', 'кофе эспрессо': '☕ Кофе', 
        'кофе эспрессо двойной': '☕ Кофе', 'красностоп, корвина 125мл': '🍷 Вино', 'крушовице 0,33': '🍾 Пиво ШТ', 
        'крушовице 0,33 б/а': '🥤 Стекло/Банка Б/А', 'крушовице темное 500мл': '🍺 Пиво Розлив', 'крушовице черне, 0,45': '🍾 Пиво ШТ', 
        'куба либре': '🍹 Коктейли', 'лайм 20г': '🍬 Доп. ингредиенты', 'ламбруско\xa0 125мл': '🍷 Вино', 
        'латте с кокосовым молоком': '☕ Кофе', 'латте с миндальным молоком': '☕ Кофе', 'ле гран 125мл': '🍷 Вино', 
        'ле гран нуар 750мл': '🍷 Вино', 'лимон 20г': '🍬 Доп. ингредиенты', 'лонг айленд айс ти': '🍹 Коктейли', 
        'май тай': '🍹 Коктейли', 'маракуйя гуава': '🍵 Чай', 'маргарита': '🍹 Коктейли', 'мейзон 500мл': '🍺 Пиво Розлив', 
        'местное светлое 1000мл': '🍺 Пиво Розлив', 'местное светлое 500мл': '🍺 Пиво Розлив', 'милк шейк ванильный': '🍓 Милк/Фреш/Смузи', 
        'милк шейк клубнично-банановый': '🍓 Милк/Фреш/Смузи', 'милк шейк лесные ягоды': '🍓 Милк/Фреш/Смузи', 
        'милк шейк шоколадный': '🍓 Милк/Фреш/Смузи', 'минеральная вода 0,33': '🥤 Стекло/Банка Б/А', 'минеральная вода 0,5': '🥤 Стекло/Банка Б/А', 
        'молоко 50мл': '🍬 Доп. ингредиенты', 'морс 250 мл': '🚰 Розлив Б/А', 'морской бриз малибу': '🍹 Коктейли', 
        'мохито б/а': '🧉 Коктейль Б/А', 'мохито в асс.': '🍹 Коктейли', 'мята 20г': '🍬 Доп. ингредиенты', 
        'мёд 50г': '🍬 Доп. ингредиенты', 'напиток газированный 0,33': '🥤 Стекло/Банка Б/А', 'напиток газированный 0,5': '🥤 Стекло/Банка Б/А', 
        'напиток газированный розлив 250 мл': '🚰 Розлив Б/А', 'напиток из сиропа биб (кфс)': '🚰 Розлив Б/А', 'негрони': '🍹 Коктейли', 
        'нк клубника базилик 40 мл': '🍒 Ликер/Настойка', 'нк кокос 40 мл': '🍒 Ликер/Настойка', 'нк сливочная лимончелло 40 мл': '🍒 Ликер/Настойка', 
        'нк черешня 40 мл': '🍒 Ликер/Настойка', 'нк щавеливая 40 мл': '🍒 Ликер/Настойка', 'нк\xa0 фейхоа мята 40 мл': '🍒 Ликер/Настойка', 
        'облепиховый чай с имбирём': '🍵 Чай', 'обнимашки': '🍹 Коктейли', 'окровавленная мерри': '🍹 Коктейли', 'онегин 40 мл': '💧 Водка', 
        'пино колада б/а': '🧉 Коктейль Б/А', 'пинья колада': '🍹 Коктейли', 'пляж лонг айленда': '🍹 Коктейли', 
        'просекко шардоне 125мл': '🍷 Вино', 'пфефферер 125мл': '🍷 Вино', 'рача': '🍹 Коктейли', 'ред бул - виски': '🍹 Коктейли', 
        'ред булл - водка': '🥤 Стекло/Банка Б/А', 'ред булл 0,25': '🥤 Стекло/Банка Б/А', 'ром кола': '🍹 Коктейли', 
        'светлое 500мл бур': '🍺 Пиво Розлив', 'сидр вп пуаре, 0,33л': '🍏 Сидр ШТ', 'сидр честерс вишня, 0,5': '🍏 Сидр ШТ', 
        'сидр честерс лесн. ягоды, 0,5': '🍏 Сидр ШТ', 'сидр честерс персик-абрикос, 0,45': '🍏 Сидр ШТ', 'сидр честерс яблоко, 0,5': '🍏 Сидр ШТ', 
        'сироп 50мл': '🍬 Доп. ингредиенты', 'сливки 50мл': '🍬 Доп. ингредиенты', 'смузи ежевичный': '🍓 Милк/Фреш/Смузи', 
        'смузи клубнично-банановый': '🍓 Милк/Фреш/Смузи', 'сок rich стекло 0,2л, шт': '🥤 Стекло/Банка Б/А', 'сок в асс. 250мл': '🚰 Розлив Б/А', 
        'сэт до еды': '🍹 Коктейли', 'сэт убийцы': '🍹 Коктейли', 'текила санрайз': '🌵 Текила', 'тини 750мл': '🍷 Вино', 
        'том коллинз': '🍹 Коктейли', 'тоник 0,33': '🥤 Стекло/Банка Б/А', 'торрес 10 лет 40мл': '🍇 Коньяк/Бренди', 'флэт уайт': '☕ Кофе', 
        'фрескеллов асс 125мл': '🍷 Вино', 'фреш апельсиновый 100 мл для комбо с яблочным': '🍓 Милк/Фреш/Смузи', 
        'фреш апельсиновый 200 мл': '🍓 Милк/Фреш/Смузи', 'фруктовый физ': '🍹 Коктейли', 'ханс баер рислинг 125мл': '🍷 Вино', 
        'ханс баер рислинг 750мл': '🍷 Вино', 'хаски 40мл': '💧 Водка', 'хаски берри микс 40мл': '💧 Водка', 'хххчай ежевика миндаль': '🍵 Чай', 
        'чай 800 мл': '🍵 Чай', 'чай акция, порц': '🍵 Чай', 'чай бардак бергамота': '🍵 Чай', 'чай брусничный': '🍵 Чай', 
        'чай да хун пао 400 мл': '🍵 Чай', 'чай ежевика миндаль_': '🍵 Чай', 'чай иван чай с малиной и травами': '🍵 Чай', 
        'чай имбирный 200': '🍵 Чай', 'чай имбирный 400': '🍵 Чай', 'чай мандариновый 200': '🍵 Чай', 'чай мандариновый 400': '🍵 Чай', 
        'чай медовое яблоко': '🍵 Чай', 'чай облепиховый 200': '🍵 Чай', 'чай облепиховый 400': '🍵 Чай', 'чай пакетированый бур, порция': '🍵 Чай', 
        'чай розмарин 200': '🍵 Чай', 'чай розмарин 400': '🍵 Чай', 'чай тегуань инь 400 мл': '🍵 Чай', 'чивас ригал 12 лет 40мл': '🥃 Виски', 
        'чистые росы 40 мл': '💧 Водка', 'шато тамань селект блан 125мл': '🍷 Вино', 'эсполон бланко 40мл': '🌵 Текила', 'ящерица лонг айленда': '🍹 Коктейли'
    }
    if name in manual_dict: return manual_dict[name]

    # РЕЗЕРВНЫЙ ПОИСК
    food_keywords = ['бургер', 'суп', 'салат', 'фри', 'сыр', 'мясо', 'стейк', 'хлеб', 'соус', 'картофель', 'гренки', 'крылья', 'креветки', 'паста', 'сухарики', 'сэндвич', 'добавка', 'десерт', 'мороженое', 'чизкейк', 'начос', 'кесадилья']
    if any(w in name for w in food_keywords): return '🍔 Еда (Кухня)'

    extra_keywords = ['сироп', 'доп.', 'сливки', 'молоко 50', 'лимон 20', 'лайм 20', 'мята 20', 'апельсин 20', 'мёд']
    if any(w in name for w in extra_keywords): return '🍬 Доп. ингредиенты'

    if any(w in name for w in ['кофе', 'капучино', 'латте', 'эспрессо', 'американо', 'раф', 'флэт уайт']): return '☕ Кофе'
    if any(w in name for w in ['чай', 'сенча', 'пуэр', 'эрл грей']): return '🍵 Чай'
    if any(w in name for w in ['смузи', 'милк', 'шейк', 'фреш']): return '🍓 Милк/Фреш/Смузи'
    if 'б/а' in name and any(w in name for w in ['мохито', 'пина', 'глинтвейн', 'коктейль']): return '🧉 Коктейль Б/А'
    if any(w in name for w in ['морс', 'лимонад', 'напиток']): 
        if not any(b in name for b in ['черноголовка', 'натахтари']): return '🚰 Розлив Б/А'
    if any(w in name for w in ['кола', 'cola', 'тоник', 'red bull', 'rich', 'вода', 'water']): return '🥤 Стекло/Банка Б/А'

    if 'сидр' in name: return '🍏 Сидр ШТ'
    if any(w in name for w in ['corona', 'clausthaler']) or ('пиво' in name and 'шт' in name): return '🍾 Пиво ШТ'
    if any(w in name for w in ['пиво', 'beer', 'ale', 'lager', 'stout', 'светлое', 'темное']): return '🍺 Пиво Розлив'
    if any(w in name for w in ['виски', 'jameson', 'jack', 'jim beam', 'macallan']): return '🥃 Виски'
    if any(w in name for w in ['водка', 'белуга', 'хаски', 'онегин', 'finlandia']): return '💧 Водка'
    if any(w in name for w in ['ром', 'bacardi', 'morgan', 'havana']): return '🏴‍☠️ Ром'
    if any(w in name for w in ['текила', 'olmeca', 'espolon']): return '🌵 Текила'
    if any(w in name for w in ['джин', 'beefeater', 'gordon', 'bombay']): return '🌲 Джин'
    if any(w in name for w in ['коньяк', 'арарат', 'hennessy']): return '🍇 Коньяк/Бренди'
    if any(w in name for w in ['ликер', 'настойка', 'егерь', 'baileys', 'апероль', 'самбука']): return '🍒 Ликер/Настойка'
    if any(w in name for w in ['вино', 'wine', 'брют', 'просекко', 'шардоне']): return '🍷 Вино'
    if any(w in name for w in ['коктейль', 'шот', 'лонг', 'дайкири', 'маргарита']): return '🍹 Коктейли'

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

def detect_header_row(df_preview, required_column):
    for idx in range(min(20, len(df_preview))):
        row_values = df_preview.iloc[idx].astype(str).str.lower()
        if row_values.str.contains(required_column.lower(), regex=False).any():
            return idx
    return None

def process_single_file(file_content, filename=""):
    warnings = []
    try:
        if isinstance(file_content, BytesIO):
            file_content.seek(0)
        try:
            df_raw = pd.read_csv(file_content, header=None, nrows=20, sep=None, engine='python')
        except (ValueError, pd.errors.ParserError):
            if isinstance(file_content, BytesIO):
                file_content.seek(0)
            df_raw = pd.read_excel(file_content, header=None, nrows=20)

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
        if not report_date:
            warnings.append(f"Не удалось определить дату отчета, используется текущая дата: {filename}")
            report_date = datetime.now()

        header_row = detect_header_row(df_raw, "Выручка с НДС")
        if header_row is None:
            warnings.append(f"Заголовок не найден, используется строка 6: {filename}")
            header_row = 5

        if isinstance(file_content, BytesIO):
            file_content.seek(0)
        try:
            df = pd.read_csv(file_content, header=header_row, sep=None, engine='python')
        except (ValueError, pd.errors.ParserError):
            if isinstance(file_content, BytesIO):
                file_content.seek(0)
            df = pd.read_excel(file_content, header=header_row)

        df.columns = df.columns.astype(str).str.strip()
        required_columns = {'Количество', 'Себестоимость', 'Выручка с НДС'}
        missing_columns = required_columns.difference(df.columns)
        if 'Выручка с НДС' not in df.columns:
            return None, f"Не найдена колонка 'Выручка с НДС' в файле: {filename}", warnings
        if missing_columns:
            warnings.append(f"В файле отсутствуют колонки: {', '.join(sorted(missing_columns))}. {filename}")

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
        df['Категория'] = df['Блюдо'].apply(detect_category_granular)
        
        # --- БЕЗОПАСНОЕ ДОБАВЛЕНИЕ ПОСТАВЩИКА ---
        if 'Поставщик' in df.columns:
            df['Поставщик'] = df['Поставщик'].fillna('Не указан')
        else:
            df['Поставщик'] = 'Не указан'
        # ----------------------------------------

        return df, None, warnings
    except (ValueError, KeyError, pd.errors.ParserError) as exc:
        return None, f"Ошибка обработки файла {filename}: {exc}", warnings

@st.cache_data(ttl=3600, show_spinner="Скачиваем данные с Яндекс.Диска...")

# --- SMART INSIGHTS ENGINE ---
def generate_insights(df_curr, df_prev, cur_rev, prev_rev, cur_fc):
    with st.expander("💡 Smart Insights (Анализ Аномалий)", expanded=True):
        alerts = []
        
        # 1. Revenue Check
        if prev_rev > 0:
            rev_diff_pct = (cur_rev - prev_rev) / prev_rev * 100
            if rev_diff_pct < -10:
                st.error(f"📉 **Тревога по Выручке**: Падение на {abs(rev_diff_pct):.1f}% по сравнению с прошлым периодом.")
                alerts.append("rev_drop")
            elif rev_diff_pct > 20:
                st.success(f"🚀 **Отличный рост**: Выручка выросла на {rev_diff_pct:.1f}%!")
                alerts.append("rev_growth")

        # 2. Food Cost Check
        TARGET_FC = 35.0
        if cur_fc > TARGET_FC:
            st.warning(f"⚠️ **Высокий Фуд-кост**: Текущий {cur_fc:.1f}% (Цель: {TARGET_FC}%).")
            alerts.append("high_fc")
        
        # 3. Ingredient Inflation (Top Spike)
        if not df_prev.empty and 'Unit_Cost' in df_curr.columns and 'Unit_Cost' in df_prev.columns:
            # Сравниваем средние цены закупки
            curr_prices = df_curr.groupby('Блюдо')['Unit_Cost'].mean()
            prev_prices = df_prev.groupby('Блюдо')['Unit_Cost'].mean()
            
            price_changes = (curr_prices - prev_prices) / prev_prices * 100
            price_changes = price_changes.dropna().sort_values(ascending=False)
            
            if not price_changes.empty:
                top_inflator = price_changes.index[0]
                top_val = price_changes.iloc[0]
                if top_val > 15: # Если выросло более чем на 15%
                    st.warning(f"💸 **Скачок цены**: {top_inflator} подорожал на {top_val:.0f}%.")
                    alerts.append("inflation")

        # 4. Dead Items ("Dogs")
        # Logic: Low Sales (< Avg) AND Low Margin (< Avg)
        if not df_curr.empty:
            item_stats = df_curr.groupby('Блюдо').agg({'Количество': 'sum', 'Выручка с НДС': 'sum', 'Себестоимость': 'sum'}).reset_index()
            item_stats['Маржа'] = item_stats['Выручка с НДС'] - item_stats['Себестоимость']
            item_stats = item_stats[item_stats['Количество'] > 0]
            
            avg_qty = item_stats['Количество'].mean()
            avg_margin = item_stats['Маржа'].mean() # Total margin per item line
            
            dogs = item_stats[(item_stats['Количество'] < avg_qty * 0.5) & (item_stats['Маржа'] < avg_margin * 0.5)]
            if len(dogs) > 5:
                st.info(f"🐶 **Мертвый груз**: Найдено {len(dogs)} позиций 'Собак' (мало продаж, мало денег). Проверьте вкладку 'Матрица'.")
                alerts.append("dogs")

        if not alerts:
            st.success("✅ **Всё спокойно**: Критических отклонений не найдено.")

def load_all_from_yandex(root_path):
    token = get_secret("YANDEX_TOKEN")
    if not token: return None
    headers = {'Authorization': f'OAuth {token}'}
    api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
    
    # helper to process a list of files with a specific venue tag
    def process_items(files, venue_tag):
        processed = []
        for item in files:
            try:
                file_resp = requests.get(item['file'], headers=headers, timeout=20)
                df, error, warnings = process_single_file(BytesIO(file_resp.content), filename=item['name'])
                if error:
                    st.warning(f"{item['name']}: {error}")
                if df is not None:
                    df['Venue'] = venue_tag
                    processed.append(df)
            except: continue
        return processed

    # 1. Get Root Items
    params = {'path': root_path, 'limit': 2000}
    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=20)
        if response.status_code != 200: return []
        items = response.json().get('_embedded', {}).get('items', [])
        
        folders = [i for i in items if i['type'] == 'dir']
        root_files = [i for i in items if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
        
        all_dfs = []
        
        # 2. Process Root Files -> Venue = 'Mesto'
        if root_files:
             all_dfs.extend(process_items(root_files, 'Mesto'))

        # 3. Recursive Process Subfolders
        def get_files_recursive(path):
            all_files_in_path = []
            try:
                p = {'path': path, 'limit': 1000}
                r = requests.get(api_url, headers=headers, params=p, timeout=20)
                if r.status_code == 200:
                    emb = r.json().get('_embedded', {})
                    itms = emb.get('items', [])
                    
                    # Files in this dir
                    files = [i for i in itms if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
                    all_files_in_path.extend(files)
                    
                    # Subdirs to recurse
                    dirs = [i for i in itms if i['type'] == 'dir']
                    for d in dirs:
                        all_files_in_path.extend(get_files_recursive(d['path']))
            except: pass
            return all_files_in_path

        for folder in folders:
            venue_name = folder['name']
            # Get all files recursively
            venue_files = get_files_recursive(folder['path'])
            
            if venue_files:
                all_dfs.extend(process_items(venue_files, venue_name))
        
        return all_dfs
    except Exception as e:
        st.error(f"Error loading from Yandex: {e}")
        return []

def load_from_local_folder(root_path):
    all_dfs = []
    
    # helper to process a list of files
    def process_local_files(files, venue_tag):
        processed = []
        for file_path in files:
            try:
                # Read file content
                with open(file_path, 'rb') as f:
                    content = BytesIO(f.read())
                
                filename = os.path.basename(file_path)
                df, error, warnings = process_single_file(content, filename=filename)
                
                if error:
                    st.warning(f"{filename}: {error}")
                if df is not None:
                    df['Venue'] = venue_tag
                    processed.append(df)
            except Exception as e:
                st.warning(f"Error reading {file_path}: {e}")
        return processed

    try:
        if not os.path.exists(root_path):
            st.error(f"Папка не найдена: {root_path}")
            return []

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
                all_dfs.extend(process_local_files(target_files, venue_name))

        return all_dfs
    except Exception as e:
        st.error(f"Error loading local files: {e}")
        return []

# --- ИНТЕРФЕЙС ЗАГРУЗКИ (Свернутый) ---
with st.sidebar.expander("⚙️ Загрузка данных / Правка", expanded=True):
    st.header("📂 1. Источник данных")
    
    # Default to Yandex Disk, hide others
    source_mode = "Яндекс.Диск"
    
    # Yandex Disk UI (Primary)
    if source_mode == "Яндекс.Диск":
        yandex_path = st.text_input("Папка на Диске:", "RestoAnalytic")
        if st.button("� Скачать отчеты", type="primary"):
            if not get_secret("YANDEX_TOKEN"):
                 st.error("⚠️ Нет токена в Secrets (локально или в облаке)!")
            else:
                temp_data = load_all_from_yandex(yandex_path)
                if temp_data:
                    st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')
                    st.success(f"Загружено {len(temp_data)} отчетов!")
                else:
                    st.warning("Файлов не найдено.")

    # Advanced / Legacy Options
    with st.expander("🛠 Расширенные настройки (Локально/Ручная)"):
        adv_source = st.radio("Альтернативный источник:", ["Нет", "Локальная папка", "Ручная загрузка"])
        
        if adv_source == "Локальная папка":
            local_path = st.text_input("Путь к папке (для Cloud укажите '.'):", ".")
            if st.button("🚀 Сканировать папку"):
                temp_data = load_from_local_folder(local_path)
                if temp_data:
                    st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')
                    st.success(f"Загружено {len(temp_data)} отчетов!")
                else:
                    st.warning("Файлов не найдено.")

        elif adv_source == "Ручная загрузка":
            uploaded_files = st.file_uploader("Загрузить отчеты (CSV/Excel)", accept_multiple_files=True)
            if uploaded_files:
                temp_data = []
                for f in uploaded_files:
                    df_res = process_single_file(f, f.name)
                    if isinstance(df_res, tuple):
                        df, error, warnings = df_res
                    else:
                        df = df_res 
                        error, warnings = None, []

                    if error:
                        st.warning(error)
                    else:
                        for warning in warnings:
                            st.warning(warning)
                    if df is not None:
                        temp_data.append(df)
                if temp_data:
                    st.session_state.df_full = pd.concat(temp_data, ignore_index=True).sort_values(by='Дата_Отчета')
                    st.success("Файлы обработаны!")

        if st.button("� Сбросить все данные"):
            st.cache_data.clear()
            st.session_state.df_full = None
            st.rerun()

    # --- CACHE LOGIC ---
    CACHE_FILE = "data_cache.parquet"

    if st.button("🚀 Проверить и загрузить из Кеша"):
        if os.path.exists(CACHE_FILE):
             st.session_state.df_full = pd.read_parquet(CACHE_FILE)
             st.success("Данные загружены из кеша (молниеносно)!")
             st.rerun()
        else:
             st.warning("Кеш пуст. Загрузите данные вручную и сохраните их.")
    
    # КНОПКА СОХРАНЕНИЯ В КЕШ
    if st.session_state.df_full is not None:
        if st.button("💾 Сохранить в Кеш (Ускорение)"):
            st.session_state.df_full.to_parquet(CACHE_FILE, index=False)
            st.success("✅ Данные сохранены в кеш! Теперь перезагрузки будут мгновенными.")
    
    st.write("---")
    st.header("🗂️ Аудит категорий (Что попало в 'Прочее')")
    
    # --- CUSTOM CATEGORY LOGIC ---
    MAPPING_FILE = "category_mapping.json"

    def load_custom_categories():
        if os.path.exists(MAPPING_FILE):
            try:
                with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_custom_categories(new_map):
        current_map = load_custom_categories()
        current_map.update(new_map)
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_map, f, ensure_ascii=False, indent=4)

    # Load custom map at startup
    if 'custom_cats' not in st.session_state:
        st.session_state.custom_cats = load_custom_categories()

    # Apply custom map to current dataframe
    if st.session_state.df_full is not None:
        # 1. Apply existing custom map
        st.session_state.df_full['Категория'] = st.session_state.df_full.apply(
            lambda x: st.session_state.custom_cats.get(x['Блюдо'], x['Категория']), axis=1
        )

        # 2. Find items in "Other"
        other_items = st.session_state.df_full[st.session_state.df_full['Категория'] == '📦 Прочее']['Блюдо'].unique()
        
        if len(other_items) > 0:
            st.warning(f"Есть {len(other_items)} нераспознанных блюд.")
            
            with st.expander("🛠 Разобрать 'Прочее' (Визуальный редактор)", expanded=True):
                # Create a form for editing
                with st.form("category_editor"):
                    col1, col2 = st.columns([2, 1])
                    
                    new_mappings = {}
                    # Show top 20 for performance
                    for item in other_items[:20]:
                        col1.write(f"**{item}**")
                        # Default category selection
                        new_cat = col2.selectbox(
                            "Категория", 
                            ["📦 Прочее", "🍔 Еда (Кухня)", "🍹 Коктейли", "☕ Кофе", "🍵 Чай", "🍺 Пиво Розлив", "🛁 Водка", "🍷 Вино"], # Add all your categories here
                            key=f"cat_{item}",
                            label_visibility="collapsed"
                        )
                        if new_cat != "📦 Прочее":
                            new_mappings[item] = new_cat
                    
                    if len(other_items) > 20:
                        st.info(f"...и еще {len(other_items)-20} позиций (сохраните текущие, чтобы увидеть следующие).")

                    if st.form_submit_button("💾 Сохранить и запомнить"):
                        if new_mappings:
                            save_custom_categories(new_mappings)
                            st.session_state.custom_cats = load_custom_categories() # Reload
                            st.success(f"Запомнено {len(new_mappings)} блюд! Перезагружаю...")
                            st.rerun()
                        else:
                            st.info("Ничего не выбрано для сохранения.")
        else:
            st.success("🎉 Все блюда распознаны! Очередь 'Прочее' пуста.")


    st.write("---")
    
    # --- TELEGRAM BOT ---
    st.header("📲 Telegram Отчет")
    tg_token = get_secret("TELEGRAM_TOKEN")
    tg_chat = get_secret("TELEGRAM_CHAT_ID")
    
    if st.button("📤 Отправить отчет в Telegram"):
        if not tg_token or not tg_chat:
            st.error("❌ Сначала добавьте TELEGRAM_TOKEN и TELEGRAM_CHAT_ID в Secrets!")
        elif st.session_state.df_full is None:
            st.warning("⚠️ Сначала загрузите данные.")
        else:
            with st.spinner("Формирую отчет..."):
                target_date = datetime.now() # Или брать из фильтра, если он есть
                report_text = telegram_utils.format_report(st.session_state.df_full, target_date)
                success, msg = telegram_utils.send_to_all(tg_token, tg_chat, report_text)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)


# --- ОСНОВНАЯ ЛОГИКА ---
if st.session_state.df_full is not None:

    # --- СЕЛЕКТОР ЗАВЕДЕНИЯ (VENUE) ---
    selected_venue = "Все заведения"
    if 'Venue' in st.session_state.df_full.columns:
        unique_venues = sorted(st.session_state.df_full['Venue'].astype(str).unique())
        if len(unique_venues) > 1 or (len(unique_venues) == 1 and unique_venues[0] != 'nan'):
             st.sidebar.markdown("---")
             st.sidebar.header("🏢 Заведение")
             selected_venue = st.sidebar.selectbox("Выберите точку:", ["Все заведения"] + unique_venues)

    # ЛЕЧЕНИЕ ДАННЫХ В ПАМЯТИ (Если вдруг нет колонки)
    if 'Поставщик' not in st.session_state.df_full.columns:
        st.session_state.df_full['Поставщик'] = 'Не указан'

    # ФИЛЬТРАЦИЯ
    if selected_venue != "Все заведения":
        df_full = st.session_state.df_full[st.session_state.df_full['Venue'] == selected_venue].copy()
    else:
        df_full = st.session_state.df_full.copy()
    df_full['Макро_Категория'] = df_full['Категория'].apply(get_macro_category)
    
    df_full['Макро_Категория'] = df_full['Категория'].apply(get_macro_category)
    
    # Кнопка скачивания moved to Settings expander

    dates_list = sorted(df_full['Дата_Отчета'].unique(), reverse=True)
    
    # --- СЕЛЕКТОР ПЕРИОДОВ ---
    st.sidebar.write("---")
    st.sidebar.header("🗓 Период Анализа")
    
    # Выбор режима: Месяц (для KPI/MoM) или Произвольный (для детального анализа)
    period_mode = st.sidebar.radio("Режим:", ["📅 Месяц (Сравнение)", "📆 Интервал дат"], label_visibility="collapsed", horizontal=True)
    
    df_current = pd.DataFrame()
    df_prev = pd.DataFrame()
    prev_label = ""
    target_date = datetime.now()
    
    if period_mode == "📅 Месяц (Сравнение)":
        df_full['Month_Year'] = df_full['Дата_Отчета'].dt.to_period('M')
        available_months = sorted(df_full['Month_Year'].unique(), reverse=True)
        
        if available_months:
            selected_month = st.sidebar.selectbox("Выбери месяц:", available_months, format_func=lambda x: x.strftime('%B %Y'))
            compare_options = ["Предыдущий месяц", "Тот же месяц (год назад)", "Нет"]
            compare_mode = st.sidebar.selectbox("Сравнить с:", compare_options)
            
            # Текущий
            df_current = df_full[df_full['Month_Year'] == selected_month]
            target_date = df_current['Дата_Отчета'].max()
            
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
        date_range = st.sidebar.date_input("Выберите даты:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_d, end_d = date_range
            df_current = df_full[(df_full['Дата_Отчета'].dt.date >= start_d) & (df_full['Дата_Отчета'].dt.date <= end_d)]
            target_date = end_d
            prev_label = "Сравнение недоступно в режиме интервала"
            compare_mode = "Нет" # Для графика
        else:
            st.warning("Выберите корректный интервал")

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
        
        sub_title = "Произвольный период" if period_mode == "📆 Интервал дат" else f"{selected_month.strftime('%B %Y')} vs {prev_label if not df_prev.empty else 'Нет данных'}"
        
        # --- SMART INSIGHTS ---
        generate_insights(df_current, df_prev, cur_rev, prev_rev, cur_fc)
        
        st.write(f"### 📊 Сводка: {sub_title}")
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("💰 Выручка", f"{cur_rev:,.0f} ₽", f"{delta_rev:+,.0f} ₽" if not df_prev.empty else None)
        kpi2.metric("📉 Фуд-кост", f"{cur_fc:.1f} %", f"{delta_fc:+.1f} %" if not df_prev.empty else None, delta_color="inverse")
        kpi3.metric("💳 Маржа", f"{cur_margin:,.0f} ₽", f"{delta_margin:+,.0f} ₽" if not df_prev.empty else None)
        kpi4.metric("🧾 Позиций", len(df_current))

        # --- ГРАФИК ДИНАМИКИ ПО ДНЯМ ---
        if period_mode == "📅 Месяц (Сравнение)" and not df_current.empty:
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
            all_items = sorted(df_full['Блюдо'].unique())
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
                supplier_stats = df_view.groupby('Поставщик')['Себестоимость'].sum().reset_index()
                supplier_stats = supplier_stats[supplier_stats['Поставщик'] != 'Не указан'].sort_values('Себестоимость', ascending=False).head(10)
                
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

        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Структура выручки")
            df_cat = df_view.groupby(target_cat)['Выручка с НДС'].sum().reset_index()
            fig_pie = px.pie(df_cat, values='Выручка с НДС', names=target_cat, hole=0.4)
            fig_pie.update_traces(hovertemplate='%{label}: %{value:,.0f} ₽ (%{percent})')
            st.plotly_chart(update_chart_layout(fig_pie), use_container_width=True)
        
        with c2:
            st.subheader("📊 Детальный анализ Фуд-коста")
            df_menu = df_view.groupby(['Блюдо', target_cat]).agg({'Выручка с НДС': 'sum', 'Себестоимость': 'sum', 'Количество': 'sum'}).reset_index()
            df_menu['Фудкост %'] = np.where(df_menu['Выручка с НДС']>0, df_menu['Себестоимость']/df_menu['Выручка с НДС']*100, 0)
            df_menu = df_menu.sort_values('Выручка с НДС', ascending=False).head(50)
            df_menu = df_menu.rename(columns={target_cat: 'Категория'})
            
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

        st.write("---")
        st.subheader("🕵️‍♀️ Аудит категорий (Что попало в 'Прочее')")
        uncategorized = df_view[df_view['Категория'].str.contains('Прочее', case=False)]['Блюдо'].unique()
        if len(uncategorized) > 0:
            st.warning(f"Есть {len(uncategorized)} нераспознанных блюд.")
            st.dataframe(pd.DataFrame(uncategorized, columns=['Нераспознанные блюда']), use_container_width=True)
        else:
            st.success("Все блюда распределены!")

    # --- 4. ABC МАТРИЦА ---
    elif selected_tab == "⭐ Матрица (ABC)":
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
        st.plotly_chart(update_chart_layout(fig_abc), use_container_width=True)

    # --- 5. ДНИ НЕДЕЛИ ---
    elif selected_tab == "🗓 Дни недели":
        st.subheader("🗓 Дни недели")
        if len(dates_list) > 1:
            df_full['ДеньНедели'] = df_full['Дата_Отчета'].dt.day_name()
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            days_rus = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
            dow_stats = df_full.groupby(['Дата_Отчета', 'ДеньНедели'])['Выручка с НДС'].sum().reset_index().groupby('ДеньНедели')['Выручка с НДС'].mean().reindex(days_order).reset_index()
            dow_stats['ДеньРус'] = days_rus
            fig_dow = px.bar(dow_stats, x='ДеньРус', y='Выручка с НДС', color='Выручка с НДС')
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
            all_cats = sorted(df_full['Категория'].dropna().unique())
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
                # Фильтрация данных
                df_sim = df_view[df_view['Категория'].isin(selected_cats)].copy()
                
                # Базовые показатели
                base_revenue = df_sim['Выручка с НДС'].sum()
                base_cost_total = df_sim['Себестоимость'].sum()
                base_margin = base_revenue - base_cost_total
                base_qty = df_sim['Количество'].sum()
                
                # Симуляция
                # Новая цена = Старая цена * (1 + %) -> Новая выручка на ед. = Старая выручка * (1 + %)
                # Новая с/с = Старая с/с * (1 + %)
                # Новое кол-во = Старое кол-во * (1 + %)
                
                sim_revenue = base_revenue * (1 + delta_price/100) * (1 + delta_vol/100)
                sim_cost_total = base_cost_total * (1 + delta_cost/100) * (1 + delta_vol/100)
                sim_margin = sim_revenue - sim_cost_total
                
                # Дельты
                diff_rev = sim_revenue - base_revenue
                diff_margin = sim_margin - base_margin
                
                st.write(f"### 📊 Прогноз результата (Категории: {len(selected_cats)})")
                
                # Метрики
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("Выручка (Sim)", f"{sim_revenue:,.0f} ₽", f"{diff_rev:+,.0f} ₽")
                kpi2.metric("Маржа (Sim)", f"{sim_margin:,.0f} ₽", f"{diff_margin:+,.0f} ₽")
                
                new_profitability = (sim_margin / sim_revenue * 100) if sim_revenue > 0 else 0
                old_profitability = (base_margin / base_revenue * 100) if base_revenue > 0 else 0
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