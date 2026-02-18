import pandas as pd
import numpy as np
import re
import os
import requests
import json
from io import BytesIO
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Union
from services import category_service, parsing_service

# --- CONSTANTS ---
CACHE_FILE = "data_cache.parquet"
SCHEMA_VERSION = "2026-02-18"
SCHEMA_META_FILE = "data_cache_meta.json"
CONFIG_FILE = "config/keywords.json"

LAST_SYNC_META = {
    "dropped_stats": {"count": 0, "cost": 0.0, "items": []},
    "warnings": [],
}

# --- IN-MEMORY STORAGE ---
_RECIPES_DB = {}
_STOCK_DF = None
_TURNOVER_HISTORY_DF = None

def get_recipes_map(): return _RECIPES_DB
def get_stock_data(): return _STOCK_DF
def get_turnover_history(): return _TURNOVER_HISTORY_DF
def get_last_sync_meta(): return LAST_SYNC_META

# --- HELPERS ---
_CONFIG = None
def _get_config() -> Dict[str, Any]:
    """
    Load configuration from JSON file with lazy loading.
    Returns empty dict on failure.
    """
    global _CONFIG
    if _CONFIG: return _CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                _CONFIG = json.load(f)
        except: _CONFIG = {}
    return _CONFIG or {}

def parse_russian_date(text: Union[str, Any]) -> Optional[datetime]:
    """
    Try to parse a date from a string supporting Russian month names
    and standard DD.MM.YYYY format.
    """
    if not isinstance(text, str): return None
    text = text.lower()
    rus_months = _get_config().get("rus_months", {})
    
    match_text = re.search(r'(\d{1,2})\s+([а-я]+)\s+(\d{4})', text)
    if match_text:
        day, month_str, year = match_text.groups()
        if month_str in rus_months:
            try:
                return datetime(int(year), rus_months[month_str], int(day))
            except ValueError: return None
            
    match_digit = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    if match_digit:
        try:
            return datetime.strptime(match_digit.group(0), '%d.%m.%Y')
        except ValueError: return None
    return None

def get_rus_month_name(month_num: int) -> str:
    """
    Get Russian name for a month number (1-12).
    """
    config = _get_config()
    names = config.get("rus_month_names", {})
    # JSON keys are strings, input might be int
    return names.get(str(month_num), str(month_num))

def detect_header_row(df_preview: pd.DataFrame, required_column: str) -> Optional[int]:
    """
    Find the index of the row containing a specific column name.
    Scans the first 20 rows.
    """
    for idx in range(min(20, len(df_preview))):
        row_values = df_preview.iloc[idx].astype(str).str.lower()
        if row_values.str.contains(required_column.lower(), regex=False).any():
            return idx
    return None

def process_single_file(file_content: Union[BytesIO, str], filename: str = "") -> Tuple[Optional[pd.DataFrame], Optional[str], List[str], Dict[str, Any]]:
    """
    Process a single Excel or CSV file into a standardized DataFrame.
    Returns: (DataFrame, ErrorMessage, Warnings, DroppedStats)
    """
    warnings = []
    dropped_stats = {'count': 0, 'cost': 0.0, 'items': []}
    
    try:
        # 1. READ RAW
        if isinstance(file_content, BytesIO):
             file_content.seek(0)
             content_for_preview = BytesIO(file_content.read())
             file_content.seek(0)
        else:
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
        rus_months = _get_config().get("rus_months", {})

        if not report_date:
            # Fallback to filename
            month_map = {
                'jan': 'января', 'feb': 'февраля', 'mar': 'марта', 'apr': 'апреля', 
                'may': 'мая', 'jun': 'июня', 'jul': 'июля', 'aug': 'августа', 
                'sep': 'сентября', 'oct': 'октября', 'nov': 'ноября', 'dec': 'декабря'
            }
            fname_lower = filename.lower()
            for eng, rus in month_map.items():
                if eng in fname_lower:
                    d_match = re.search(r'(\d{1,2})', filename)
                    if d_match:
                        y_match = re.search(r'(20\d{2})', filename)
                        current_year = int(y_match.group(1)) if y_match else datetime.now().year
                        if rus in rus_months:
                            report_date = datetime(current_year, rus_months[rus], int(d_match.group(1)))
                            break
        
        if not report_date:
            warnings.append(f"Дата отчета не определена: {filename}")
            return None, "Не удалось определить дату отчета", warnings, dropped_stats

        # 3. LOCATE HEADER
        header_row = detect_header_row(df_raw, "Выручка с НДС")
        if header_row is None:
            warnings.append(f"Заголовок не найден, используется строка 6: {filename}")
            header_row = 5

        # 4. READ FULL
        file_content.seek(0)
        try:
            df = pd.read_csv(file_content, header=header_row, sep=None, engine='python')
        except:
            file_content.seek(0)
            df = pd.read_excel(file_content, header=header_row)

        df.columns = df.columns.astype(str).str.strip()
        
        required_cols = ['Количество', 'Себестоимость', 'Выручка с НДС']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return None, f"Не найдены обязательные колонки: {', '.join(missing_cols)}", warnings, dropped_stats

        # 5. CLEAN
        for col in required_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        col_name = df.columns[0]
        
        # 6. MULTI-DAY HANDLING
        first_col_raw = df[col_name].astype(str).str.strip()
        date_tokens = first_col_raw.str.extract(r'(?P<d>\d{2}\.\d{2}\.\d{4})', expand=True)['d']
        row_dates = pd.to_datetime(date_tokens, format='%d.%m.%Y', errors='coerce')
        unique_row_dates = row_dates.dropna().dt.normalize().nunique()

        if unique_row_dates > 1:
            df['Дата_Отчета'] = row_dates.dt.normalize().ffill()
            df = df[row_dates.isna()].copy()
            df = df[df['Дата_Отчета'].notna()].copy()
        else:
            df['Дата_Отчета'] = report_date

        # 7. FILTERING
        df['norm_name'] = df[col_name].astype(str).str.strip()
        ignore_names = _get_config().get("ignore_names", [])
        
        mask_valid_name = df[col_name].notna()
        mask_not_ignore = ~df['norm_name'].isin(ignore_names)
        mask_not_total = ~df['norm_name'].str.contains("Итого", case=False)
        
        mask_keep = mask_valid_name & mask_not_ignore & mask_not_total
        
        df_dropped = df[~mask_keep].copy()
        if not df_dropped.empty:
            dropped_stats['count'] = len(df_dropped)
            if 'Себестоимость' in df_dropped.columns:
                dropped_stats['cost'] = df_dropped['Себестоимость'].sum()
            dropped_stats['items'] = df_dropped[['norm_name', 'Себестоимость']].to_dict('records')

        df = df[mask_keep].copy()
        
        # 8. ENRICH
        df['Unit_Cost'] = np.where(df['Количество'] != 0, df['Себестоимость'] / df['Количество'], 0)
        df['Фудкост'] = np.where(df['Выручка с НДС'] > 0, (df['Себестоимость'] / df['Выручка с НДС'] * 100), 0)
        df = df.rename(columns={col_name: 'Блюдо'})
        
        df = category_service.apply_categories(df)
        
        if 'Поставщик' in df.columns:
            df['Поставщик'] = df['Поставщик'].fillna('Не указан')
        else:
            df['Поставщик'] = 'Не указан'

        return df, None, warnings, dropped_stats

    except Exception as exc:
        return None, f"Ошибка обработки: {exc}", warnings, dropped_stats

def download_and_process_yandex(yandex_token: str, yandex_path: str = "RestoAnalytic") -> Tuple[bool, str]:
    """
    Sync data from Yandex.Disk, process files, and update the cache.
    Returns: (Success, Message)
    """
    if not yandex_token:
        return False, "Не задан токен Яндекс.Диска."

    headers = {"Authorization": f"OAuth {yandex_token}"}
    api_url = "https://cloud-api.yandex.net/v1/disk/resources"
    data_frames = []
    dropped_total = {"count": 0, "cost": 0.0}
    dropped_items = []
    warnings_total = []
    
    global _RECIPES_DB, _STOCK_DF, _TURNOVER_HISTORY_DF
    recipes_list = []
    stock_parts = []
    turnover_history_parts = []

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
        if items is None: return []
        files = [i for i in items if i.get("type") == "file"]
        dirs = [i for i in items if i.get("type") == "dir"]
        result = [f for f in files if str(f.get("name", "")).lower().endswith((".xlsx", ".csv"))]
        for d in dirs:
            result.extend(get_files_recursive(d.get("path")))
        return result

    def process_remote_file(file_meta, venue):
        file_url = file_meta.get("file")
        filename = file_meta.get("name", "")
        if not file_url: return
        
        path = str(file_meta.get("path", ""))
        
        resp = requests.get(file_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            warnings_total.append(f"Не удалось скачать: {filename}")
            return
            
        content = BytesIO(resp.content)
        
        if "TechnologicalMaps" in path:
            res_list, err = parsing_service.parse_ttk(content, filename)
            if err: warnings_total.append(f"TTK Error {filename}: {err}")
            elif res_list: recipes_list.extend(res_list)
            return

        if "ProductTurnover" in path:
            df_turn, df_hist, err = parsing_service.parse_turnover(content, filename)
            if err: warnings_total.append(f"Turnover Error {filename}: {err}")
            else:
                if df_turn is not None:
                    report_ts = file_meta.get("modified") or file_meta.get("created")
                    if report_ts:
                        df_turn["report_date"] = report_ts
                    stock_parts.append(df_turn)
                if df_hist is not None and not df_hist.empty:
                    turnover_history_parts.append(df_hist)
            return

        if "TechnologicalMaps" not in path and "ProductTurnover" not in path:
            df, err, warns, dropped = process_single_file(content, filename=filename)
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
        
        root_files = [i for i in root_items if i.get("type") == "file" and str(i.get("name", "")).lower().endswith((".xlsx", ".csv"))]
        subfolders = [i for i in root_items if i.get("type") == "dir"]

        for f in root_files:
            process_remote_file(f, "Mesto")
            
        for folder in subfolders:
            venue = folder.get("name", "Unknown")
            for f in get_files_recursive(folder.get("path")):
                process_remote_file(f, venue)

        if not data_frames and not recipes_list and not stock_parts:
             return False, "Файлы найдены, но данные не были распознаны."

        if data_frames:
            full_df = pd.concat(data_frames, ignore_index=True)
            if "Дата_Отчета" in full_df.columns:
                full_df["Дата_Отчета"] = pd.to_datetime(full_df["Дата_Отчета"], errors="coerce")
                full_df = full_df.dropna(subset=["Дата_Отчета"]).sort_values("Дата_Отчета")
            full_df.to_parquet(CACHE_FILE, index=False)
            with open(SCHEMA_META_FILE, "w", encoding="utf-8") as f:
                json.dump({"schema_version": SCHEMA_VERSION}, f)

        # Update Globals
        _RECIPES_DB = {}
        for r in recipes_list:
            _RECIPES_DB[r['dish_name']] = r['ingredients']
            
        if stock_parts:
            _STOCK_DF = pd.concat(stock_parts, ignore_index=True)
            if "report_date" in _STOCK_DF.columns:
                _STOCK_DF["report_date"] = pd.to_datetime(_STOCK_DF["report_date"], errors="coerce")
                _STOCK_DF = _STOCK_DF.sort_values("report_date")
                _STOCK_DF = _STOCK_DF.groupby("ingredient", as_index=False).last()
            else:
                _STOCK_DF = _STOCK_DF.groupby("ingredient", as_index=False).last()
        else:
            _STOCK_DF = None
            
        if turnover_history_parts:
            _TURNOVER_HISTORY_DF = pd.concat(turnover_history_parts, ignore_index=True)
            _TURNOVER_HISTORY_DF = _TURNOVER_HISTORY_DF.drop_duplicates()
        else:
            _TURNOVER_HISTORY_DF = None

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

        msg = f"Обновлено строк продаж: {len(full_df) if data_frames else 0}. "
        msg += f"Рецептов: {len(_RECIPES_DB)}. Товаров: {len(_STOCK_DF) if _STOCK_DF is not None else 0}."
        if warnings_total:
            msg += f" Предупреждений: {len(warnings_total)}."
            
        return True, msg
    except Exception as exc:
        LAST_SYNC_META["warnings"] = [str(exc)]
        return False, f"Ошибка синхронизации: {exc}"

def get_recipes_map() -> Dict[str, List[Dict[str, Any]]]:
    return _RECIPES_DB
