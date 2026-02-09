import re
from datetime import datetime
from io import BytesIO

import numpy as np
import pandas as pd

from categories import MANUAL_CATEGORIES

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


def get_macro_category(cat):
    if cat in ['☕ Кофе', '🍵 Чай', '🍓 Милк/Фреш/Смузи', '🧉 Коктейль Б/А', '🚰 Розлив Б/А', '🥤 Стекло/Банка Б/А']:
        return '☕ Безалкогольное'
    if cat in ['🍏 Сидр ШТ', '🍾 Пиво ШТ', '🍺 Пиво Розлив']:
        return '🍺 Пиво/Сидр'
    if cat in ['🥃 Виски', '💧 Водка', '🏴‍☠️ Ром', '🌵 Текила', '🌲 Джин', '🍇 Коньяк/Бренди', '🍒 Ликер/Настойка']:
        return '🥃 Крепкое'
    return cat


def detect_category_granular(name_input):
    name = str(name_input).strip().lower()

    if name in MANUAL_CATEGORIES:
        return MANUAL_CATEGORIES[name]

    food_keywords = [
        'бургер', 'суп', 'салат', 'фри', 'сыр', 'мясо', 'стейк', 'хлеб', 'соус',
        'картофель', 'гренки', 'крылья', 'креветки', 'паста', 'сухарики', 'сэндвич',
        'добавка', 'десерт', 'мороженое', 'чизкейк', 'начос', 'кесадилья'
    ]
    if any(w in name for w in food_keywords):
        return '🍔 Еда (Кухня)'

    extra_keywords = ['сироп', 'доп.', 'сливки', 'молоко 50', 'лимон 20', 'лайм 20', 'мята 20', 'апельсин 20', 'мёд']
    if any(w in name for w in extra_keywords):
        return '🍬 Доп. ингредиенты'

    if any(w in name for w in ['кофе', 'капучино', 'латте', 'эспрессо', 'американо', 'раф', 'флэт уайт']):
        return '☕ Кофе'
    if any(w in name for w in ['чай', 'сенча', 'пуэр', 'эрл грей']):
        return '🍵 Чай'
    if any(w in name for w in ['смузи', 'милк', 'шейк', 'фреш']):
        return '🍓 Милк/Фреш/Смузи'
    if 'б/а' in name and any(w in name for w in ['мохито', 'пина', 'глинтвейн', 'коктейль']):
        return '🧉 Коктейль Б/А'
    if any(w in name for w in ['морс', 'лимонад', 'напиток']):
        if not any(b in name for b in ['черноголовка', 'натахтари']):
            return '🚰 Розлив Б/А'
    if any(w in name for w in ['кола', 'cola', 'тоник', 'red bull', 'rich', 'вода', 'water']):
        return '🥤 Стекло/Банка Б/А'

    if 'сидр' in name:
        return '🍏 Сидр ШТ'
    if any(w in name for w in ['corona', 'clausthaler']) or ('пиво' in name and 'шт' in name):
        return '🍾 Пиво ШТ'
    if any(w in name for w in ['пиво', 'beer', 'ale', 'lager', 'stout', 'светлое', 'темное']):
        return '🍺 Пиво Розлив'
    if any(w in name for w in ['виски', 'jameson', 'jack', 'jim beam', 'macallan']):
        return '🥃 Виски'
    if any(w in name for w in ['водка', 'белуга', 'хаски', 'онегин', 'finlandia']):
        return '💧 Водка'
    if any(w in name for w in ['ром', 'bacardi', 'morgan', 'havana']):
        return '🏴‍☠️ Ром'
    if any(w in name for w in ['текила', 'olmeca', 'espolon']):
        return '🌵 Текила'
    if any(w in name for w in ['джин', 'beefeater', 'gordon', 'bombay']):
        return '🌲 Джин'
    if any(w in name for w in ['коньяк', 'арарат', 'hennessy']):
        return '🍇 Коньяк/Бренди'
    if any(w in name for w in ['ликер', 'настойка', 'егерь', 'baileys', 'апероль', 'самбука']):
        return '🍒 Ликер/Настойка'
    if any(w in name for w in ['вино', 'wine', 'брют', 'просекко', 'шардоне']):
        return '🍷 Вино'
    if any(w in name for w in ['коктейль', 'шот', 'лонг', 'дайкири', 'маргарита']):
        return '🍹 Коктейли'

    return '📦 Прочее'


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
            month_map = {
                'jan': 'января', 'feb': 'февраля', 'mar': 'марта', 'apr': 'апреля',
                'may': 'мая', 'jun': 'июня', 'jul': 'июля', 'aug': 'августа',
                'sep': 'сентября', 'oct': 'октября', 'nov': 'ноября', 'dec': 'декабря'
            }
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

        if 'Поставщик' in df.columns:
            df['Поставщик'] = df['Поставщик'].fillna('Не указан')
        else:
            df['Поставщик'] = 'Не указан'

        return df, None, warnings
    except (ValueError, KeyError, pd.errors.ParserError) as exc:
        return None, f"Ошибка обработки файла {filename}: {exc}", warnings
