import pandas as pd
import numpy as np
import re
import os
import requests
from io import BytesIO
from datetime import datetime

# --- CONSTANTS ---
IGNORE_NAMES = [
    "Бар Место", "Бар Место Бургерная", "Итого", "Номенклатура", "Склады", 
    "Незавершённое производство", "Товары", "Услуги", "ЕГАИС", "Алкоголь",
    "Пиво разливное Россия", "Пиво импортное", "Пиво бутылочное", "Сидр", 
    "Водка", "Самогон", "Настойки", "Чача/Грапа", "Джин", "Виски/Бурбон", 
    "Текила", "Ром", "Коньяк/Бренди", "Аперитивы", "Ликеры и настойки", 
    "Вермуты", "Игристые вина", "Тихие белые вина", "Тихие розовые вина", 
    "Тихие красные вина", "Крепленые вина", "Б/а напитки", "Коктейли по контракту"
]

RUS_MONTHS = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6,
    'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
    'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
    'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12
}

RUS_MONTH_NAMES = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель', 5: 'Май', 6: 'Июнь',
    7: 'Июль', 8: 'Август', 9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}

CACHE_FILE = "data_cache.parquet"
LAST_SYNC_META = {
    "dropped_stats": {"count": 0, "cost": 0.0, "items": []},
    "warnings": [],
}

# --- HELPERS ---
def parse_russian_date(text):
    if not isinstance(text, str): return None
    text = text.lower()
    match_text = re.search(r'(\d{1,2})\s+([а-я]+)\s+(\d{4})', text)
    if match_text:
        day, month_str, year = match_text.groups()
        if month_str in RUS_MONTHS:
            try:
                return datetime(int(year), RUS_MONTHS[month_str], int(day))
            except ValueError: return None
    match_digit = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    if match_digit:
        try:
            return datetime.strptime(match_digit.group(0), '%d.%m.%Y')
        except ValueError: return None
    return None

def detect_header_row(df_preview, required_column):
    for idx in range(min(20, len(df_preview))):
        row_values = df_preview.iloc[idx].astype(str).str.lower()
        if row_values.str.contains(required_column.lower(), regex=False).any():
            return idx
    return None

from services import category_service

def get_macro_category(cat):
    if cat in ['☕ Кофе', '🍵 Чай', '🍓 Милк/Фреш/Смузи', '🧉 Коктейль Б/А', '🚰 Розлив Б/А', '🥤 Стекло/Банка Б/А']: 
        return '☕ Безалкогольное'
    if cat in ['🍏 Сидр ШТ', '🍾 Пиво ШТ', '🍺 Пиво Розлив']: 
        return '🍺 Пиво/Сидр'
    if cat in ['🥃 Виски', '💧 Водка', '🏴‍☠️ Ром', '🌵 Текила', '🌲 Джин', '🍇 Коньяк/Бренди', '🍒 Ликер/Настойка']: 
        return '🥃 Крепкое'
    return cat

def detect_category_granular(name_input, mapping=None):
    name = str(name_input).strip().lower()
    
    # 1. DYNAMIC MAPPING (JSON)
    # Check exact match first
    # mapping keys might be original case, so we should check carefully
    # Assuming mapping keys are case-sensitive or we lower them?
    # Let's assume exact match for now as per `admin_view` editor
    if mapping:
        if name in mapping:
            return mapping[name]
        if name_input in mapping:
            return mapping[name_input]
    
    # 2. HARDCODED FALLBACK (Original Dictionary)
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
    if any(w in name for w in ['cola', 'тоник', 'red bull', 'rich', 'вода', 'water', 'кола']): return '🥤 Стекло/Банка Б/А'

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

# --- CORE PARSING ---
def process_single_file(file_content, filename=""):
    """
    Parses a single Excel/CSV file into a DataFrame.
    Returns: (DataFrame, error_message, warnings, dropped_stats)
    dropped_stats is a dict: {'count': int, 'cost': float, 'items': list}
    """
    warnings = []
    dropped_stats = {'count': 0, 'cost': 0.0, 'items': []}
    
    try:
        # 1. READ RAW (Snippet for header detection)
        if isinstance(file_content, BytesIO):
             file_content.seek(0)
             content_for_preview = BytesIO(file_content.read())
             file_content.seek(0) # Reset main pointer
        else:
             # If it's a file path, read bytes
             with open(file_content, 'rb') as f:
                 raw_bytes = f.read()
             file_content = BytesIO(raw_bytes)
             content_for_preview = BytesIO(raw_bytes)

        try:
            df_raw = pd.read_csv(content_for_preview, header=None, nrows=20, sep=None, engine='python')
        except:
            content_for_preview.seek(0)
            df_raw = pd.read_excel(content_for_preview, header=None, nrows=20)

        # 2. DETECT DATE
        header_text = " ".join(df_raw.iloc[0:10, 0].astype(str).tolist())
        report_date = parse_russian_date(header_text)

        if not report_date:
            month_map = {'jan': 'января', 'feb': 'февраля', 'mar': 'марта', 'apr': 'апреля', 'may': 'мая', 'jun': 'июня', 'jul': 'июля', 'aug': 'августа', 'sep': 'сентября', 'oct': 'октября', 'nov': 'ноября', 'dec': 'декабря'}
            for eng, rus in month_map.items():
                if eng in filename.lower():
                    d_match = re.search(r'(\d{1,2})', filename)
                    if d_match:
                        # Try to find year in filename
                        y_match = re.search(r'(20\d{2})', filename)
                        current_year = int(y_match.group(1)) if y_match else datetime.now().year
                        
                        report_date = datetime(current_year, RUS_MONTHS[rus], int(d_match.group(1)))
                        break
        
        if not report_date:
            warnings.append(f"Дата отчета не определена: {filename}")
            return None, "Не удалось определить дату отчета", warnings, dropped_stats

        # 3. LOCATE HEADER ROW
        header_row = detect_header_row(df_raw, "Выручка с НДС")
        if header_row is None:
            warnings.append(f"Заголовок не найден, используется строка 6: {filename}")
            header_row = 5

        # 4. READ FULL DATAFRAME
        file_content.seek(0)
        try:
            df = pd.read_csv(file_content, header=header_row, sep=None, engine='python')
        except:
            file_content.seek(0)
            df = pd.read_excel(file_content, header=header_row)

        df.columns = df.columns.astype(str).str.strip()
        
        # VALIDATE COLUMNS
        required_cols = ['Количество', 'Себестоимость', 'Выручка с НДС']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return None, f"Не найдены обязательные колонки: {', '.join(missing_cols)}", warnings, dropped_stats

        # 5. CLEAN & CONVERT NUMBERS
        cols_to_num = ['Количество', 'Себестоимость', 'Выручка с НДС']
        for col in cols_to_num:
            if col in df.columns:
                # Keep original for debug before conversion? No, convert first
                df[col] = df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        col_name = df.columns[0] # Usually "Номенклатура" or "Блюдо"
        
        # 6. HANDLE MULTI-DAY FILES (Date markers inside first column)
        # Example marker: "01.01.2025 17:00:00" followed by item rows.
        first_col_raw = df[col_name].astype(str).str.strip()
        date_tokens = first_col_raw.str.extract(r'(?P<d>\d{2}\.\d{2}\.\d{4})', expand=True)['d']
        row_dates = pd.to_datetime(date_tokens, format='%d.%m.%Y', errors='coerce')
        unique_row_dates = row_dates.dropna().dt.normalize().nunique()

        if unique_row_dates > 1:
            df['Дата_Отчета'] = row_dates.dt.normalize().ffill()
            # Rows containing date markers are structural rows, exclude from item lines.
            df = df[row_dates.isna()].copy()
            # Keep only rows that have a resolved day after forward fill.
            df = df[df['Дата_Отчета'].notna()].copy()
        else:
            df['Дата_Отчета'] = report_date

        # 7. CAPTURE DROPPED ROWS (DEBUG)
        # Identify rows that would be dropped
        # A. Empty Identifiers
        # B. Ignore Names
        # C. "Итого" rows
        
        # We need to compute 'dropped' before we actually drop them to sum their metrics
        
        # Normalized Identifier
        df['norm_name'] = df[col_name].astype(str).str.strip()
        
        # Filter Masks
        mask_valid_name = df[col_name].notna()
        mask_not_ignore = ~df['norm_name'].isin(IGNORE_NAMES)
        mask_not_total = ~df['norm_name'].str.contains("Итого", case=False)
        
        mask_keep = mask_valid_name & mask_not_ignore & mask_not_total
        
        # Extract Dropped Data
        df_dropped = df[~mask_keep].copy()
        if not df_dropped.empty:
            dropped_stats['count'] = len(df_dropped)
            if 'Себестоимость' in df_dropped.columns:
                dropped_stats['cost'] = df_dropped['Себестоимость'].sum()
            
            # Save top 50 dropped items for review
            items_list = df_dropped[['norm_name', 'Себестоимость']].to_dict('records')
            dropped_stats['items'] = items_list

        # Apply Filter
        df = df[mask_keep].copy()
        
        # 8. ENRICH DATA
        df['Unit_Cost'] = np.where(df['Количество'] != 0, df['Себестоимость'] / df['Количество'], 0)
        df['Фудкост'] = np.where(df['Выручка с НДС'] > 0, (df['Себестоимость'] / df['Выручка с НДС'] * 100), 0)
        df = df.rename(columns={col_name: 'Блюдо'})
        
        # Load mapping once per file (or rely on cache)
        cat_mapping = category_service.load_categories()
        df['Категория'] = df['Блюдо'].apply(lambda x: detect_category_granular(x, cat_mapping))
        df['Макро_Категория'] = df['Категория'].apply(get_macro_category)
        
        # Helper for vendor
        if 'Поставщик' in df.columns:
            df['Поставщик'] = df['Поставщик'].fillna('Не указан')
        else:
            df['Поставщик'] = 'Не указан'

        return df, None, warnings, dropped_stats

    except Exception as exc:
        return None, f"Ошибка обработки: {exc}", warnings, dropped_stats

# --- ANALYTICS ---
def calculate_insights(df_curr, df_prev, cur_rev, prev_rev, cur_fc):
    """
    Calculates business insights/alerts based on current and previous data.
    Returns a list of dicts: {'type': str, 'message': str, 'level': str}
    Levels: 'success', 'warning', 'error', 'info'
    """
    insights = []
    
    # 1. Revenue Check
    if prev_rev > 0:
        rev_diff_pct = (cur_rev - prev_rev) / prev_rev * 100
        if rev_diff_pct < -10:
            insights.append({
                'type': 'rev_drop',
                'message': f"📉 **Тревога по Выручке**: Падение на {abs(rev_diff_pct):.1f}% по сравнению с прошлым периодом.",
                'level': 'error'
            })
        elif rev_diff_pct > 20:
            insights.append({
                'type': 'rev_growth',
                'message': f"🚀 **Отличный рост**: Выручка выросла на {rev_diff_pct:.1f}%!",
                'level': 'success'
            })

    # 2. Food Cost Check
    TARGET_FC = 35.0
    if cur_fc > TARGET_FC:
        insights.append({
            'type': 'high_fc',
            'message': f"⚠️ **Высокий Фуд-кост**: Текущий {cur_fc:.1f}% (Цель: {TARGET_FC}%).",
            'level': 'warning'
        })
    
    # 3. Ingredient Inflation (Top Spike)
    if not df_prev.empty and 'Unit_Cost' in df_curr.columns and 'Unit_Cost' in df_prev.columns:
        # Compare average purchase prices
        curr_prices = df_curr.groupby('Блюдо')['Unit_Cost'].mean()
        prev_prices = df_prev.groupby('Блюдо')['Unit_Cost'].mean()
        
        safe_prev_prices = prev_prices.replace(0, np.nan)
        price_changes = (curr_prices - safe_prev_prices) / safe_prev_prices * 100
        price_changes = price_changes.replace([np.inf, -np.inf], np.nan).dropna().sort_values(ascending=False)
        
        if not price_changes.empty:
            top_inflator = price_changes.index[0]
            top_val = price_changes.iloc[0]
            if top_val > 15: # Raised/Spiked more than 15%
                insights.append({
                    'type': 'inflation',
                    'message': f"💸 **Скачок цены**: {top_inflator} подорожал на {top_val:.0f}%.",
                    'level': 'warning'
                })

    # 4. Dead Items ("Dogs")
    # Logic: Low Sales (< Avg) AND Low Margin (< Avg)
    if not df_curr.empty:
        item_stats = df_curr.groupby('Блюдо').agg({'Количество': 'sum', 'Выручка с НДС': 'sum', 'Себестоимость': 'sum'}).reset_index()
        item_stats['Маржа'] = item_stats['Выручка с НДС'] - item_stats['Себестоимость']
        item_stats = item_stats[item_stats['Количество'] > 0]
        
        if not item_stats.empty:
            avg_qty = item_stats['Количество'].mean()
            avg_margin = item_stats['Маржа'].mean()
            
            dogs = item_stats[(item_stats['Количество'] < avg_qty * 0.5) & (item_stats['Маржа'] < avg_margin * 0.5)]
            if len(dogs) > 5:
                insights.append({
                    'type': 'dogs',
                    'message': f"🐶 **Мертвый груз**: Найдено {len(dogs)} позиций 'Собак' (мало продаж, мало денег).",
                    'level': 'info'
                })

    if not insights:
        insights.append({
            'type': 'all_good',
            'message': "✅ **Всё спокойно**: Критических отклонений не найдено.",
            'level': 'success'
        })

    return insights

def get_last_sync_meta():
    return LAST_SYNC_META


def download_and_process_yandex(yandex_token, yandex_path="RestoAnalytic"):
    if not yandex_token:
        return False, "Не задан токен Яндекс.Диска."

    headers = {"Authorization": f"OAuth {yandex_token}"}
    api_url = "https://cloud-api.yandex.net/v1/disk/resources"
    data_frames = []
    dropped_total = {"count": 0, "cost": 0.0}
    dropped_items = []
    warnings_total = []

    def list_items(path, limit=1000):
        items = []
        offset = 0
        while True:
            resp = requests.get(
                api_url,
                headers=headers,
                params={"path": path, "limit": limit, "offset": offset},
                timeout=20,
            )
            if resp.status_code != 200:
                return None
            page = resp.json().get("_embedded", {}).get("items", [])
            if not page:
                break
            items.extend(page)
            if len(page) < limit:
                break
            offset += limit
        return items

    def get_files_recursive(path):
        items = list_items(path)
        if items is None:
            return []
        files = [i for i in items if i.get("type") == "file"]
        dirs = [i for i in items if i.get("type") == "dir"]
        result = [f for f in files if str(f.get("name", "")).lower().endswith((".xlsx", ".csv"))]
        for d in dirs:
            result.extend(get_files_recursive(d.get("path")))
        return result

    def process_remote_file(file_meta, venue):
        file_url = file_meta.get("file")
        filename = file_meta.get("name", "")
        if not file_url:
            return
        resp = requests.get(file_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            warnings_total.append(f"Не удалось скачать: {filename}")
            return
        df, err, warns, dropped = process_single_file(BytesIO(resp.content), filename=filename)
        warnings_total.extend(warns)
        dropped_total["count"] += dropped.get("count", 0)
        dropped_total["cost"] += float(dropped.get("cost", 0.0))
        dropped_items.extend(dropped.get("items", []))
        if err:
            warnings_total.append(f"{filename}: {err}")
            return
        if df is not None and not df.empty:
            df["Точка"] = venue
            data_frames.append(df)

    try:
        root_items = list_items(yandex_path)
        if root_items is None:
            return False, "Ошибка доступа к папке на Яндекс.Диске."
        root_files = [
            i for i in root_items
            if i.get("type") == "file" and str(i.get("name", "")).lower().endswith((".xlsx", ".csv"))
        ]
        subfolders = [i for i in root_items if i.get("type") == "dir"]

        for f in root_files:
            process_remote_file(f, "Mesto")
        for folder in subfolders:
            venue = folder.get("name", "Unknown")
            for f in get_files_recursive(folder.get("path")):
                process_remote_file(f, venue)

        if not data_frames:
            return False, "Файлы найдены, но данные не были распознаны."

        full_df = pd.concat(data_frames, ignore_index=True)
        if "Дата_Отчета" in full_df.columns:
            full_df["Дата_Отчета"] = pd.to_datetime(full_df["Дата_Отчета"], errors="coerce")
            full_df = full_df.dropna(subset=["Дата_Отчета"]).sort_values("Дата_Отчета")
        full_df.to_parquet(CACHE_FILE, index=False)

        dropped_df = pd.DataFrame(dropped_items)
        if not dropped_df.empty and "Себестоимость" in dropped_df.columns:
            dropped_df = dropped_df.sort_values(by="Себестоимость", ascending=False)
            dropped_top = dropped_df.head(50).to_dict("records")
        else:
            dropped_top = dropped_items[:50]

        LAST_SYNC_META["dropped_stats"] = {
            "count": int(dropped_total["count"]),
            "cost": float(dropped_total["cost"]),
            "items": dropped_top,
        }
        LAST_SYNC_META["warnings"] = warnings_total

        msg = f"Обновлено строк: {len(full_df)}. Отброшено: {dropped_total['count']}."
        if warnings_total:
            msg += f" Предупреждений: {len(warnings_total)}."
        return True, msg
    except Exception as exc:
        LAST_SYNC_META["warnings"] = [str(exc)]
        return False, f"Ошибка синхронизации: {exc}"
