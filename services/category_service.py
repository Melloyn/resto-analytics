import json
import os
import requests
import pandas as pd
import streamlit as st
from typing import List, Dict, Any, Optional, Union
from services import parsing_service

MAPPING_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "categories.json")
YANDEX_MAPPING_PATH = "RestoAnalytic/config/categories.json"

DEFAULT_CATEGORIES = [
    "🍔 Еда (Кухня)", "🍹 Коктейли", "☕ Кофе", "🍵 Чай", "🍺 Пиво Розлив", "💧 Водка",
    "🍷 Вино", "🥤 Стекло/Банка Б/А", "🚰 Розлив Б/А", "🍓 Милк/Фреш/Смузи", 
    "🍏 Сидр ШТ", "🍾 Пиво ШТ", "🥃 Виски", "💧 Водка", "🏴‍☠️ Ром", 
    "🌵 Текила", "🌲 Джин", "🍇 Коньяк/Бренди", "🍒 Ликер/Настойка", "🍬 Доп. ингредиенты",
    "🧉 Коктейль Б/А", "📦 Прочее", "⛔ Исключить из отчетов"
]

def load_categories() -> Dict[str, str]:
    """Load category mapping from local JSON."""
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading categories: {e}")
            return {}
    return {}

def save_categories(new_map: Dict[str, str]) -> Dict[str, str]:
    """Save category mapping to local JSON."""
    current = load_categories()
    current.update(new_map)
    try:
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=4)
            print(f"Updated categories saved to {MAPPING_FILE}")
    except Exception as e:
        print(f"Error saving categories: {e}")
    return current

def save_categories_full(full_map: Dict[str, str]) -> Dict[str, str]:
    """Overwrite full category mapping JSON."""
    try:
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(full_map, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving full categories: {e}")
    return full_map

def get_all_known_categories() -> List[str]:
    """Return list of all unique categories (defaults + used in mapping)."""
    mapping = load_categories()
    cats = set(DEFAULT_CATEGORIES)
    if mapping:
        cats.update(mapping.values())
    return sorted(list(cats))

def sync_from_yandex(token: str, remote_path: str = YANDEX_MAPPING_PATH) -> bool:
    """Download categories.json from Yandex Disk."""
    if not token: return False
    headers = {'Authorization': f'OAuth {token}'}
    try:
        # Get download link
        resp = requests.get(
            "https://cloud-api.yandex.net/v1/disk/resources/download",
            headers=headers,
            params={'path': remote_path},
            timeout=5
        )
        if resp.status_code == 200:
            href = resp.json().get("href")
            dl = requests.get(href)
            if dl.status_code == 200:
                # Merge logic: Remote + Local (Local wins on conflict)
                try:
                    remote_data = dl.json()
                except:
                    # Fallback if direct json decode fails (e.g. BOM)
                    try:
                        remote_data = json.loads(dl.content.decode('utf-8-sig'))
                    except:
                        print("Failed to parse remote JSON")
                        return False

                if not isinstance(remote_data, dict):
                    remote_data = {}

                local_data = load_categories()
                
                # Merge logic: Local (base) + Remote (updates). 
                # Remote entries MUST overwrite local ones to ensure we get the latest state from cloud.
                merged = local_data.copy()
                merged.update(remote_data)
                
                with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
                    json.dump(merged, f, ensure_ascii=False, indent=4)
                print("Synced from Yandex successfully.")
                return True
        elif resp.status_code == 404:
            # Remote file doesn't exist yet, that's fine, keep local
            print("Remote categories not found (404).")
            return True
    except Exception as e:
        print(f"Sync error (from): {e}")
    return False

def sync_to_yandex(token: str, remote_path: str = YANDEX_MAPPING_PATH) -> bool:
    """Upload categories.json to Yandex Disk."""
    if not token or not os.path.exists(MAPPING_FILE): return False
    headers = {'Authorization': f'OAuth {token}'}
    try:
        # Get upload link
        resp = requests.get(
            "https://cloud-api.yandex.net/v1/disk/resources/upload",
            headers=headers,
            params={'path': remote_path, 'overwrite': 'true'},
            timeout=5
        )
        if resp.status_code == 200:
            href = resp.json().get("href")
            with open(MAPPING_FILE, 'rb') as f:
                # Use data=f for raw body upload, not files= (multipart)
                up = requests.put(href, data=f)
                if up.status_code in [201, 202]:
                    print("Synced to Yandex successfully.")
                    return True
                else:
                    print(f"Upload failed: {up.status_code} {up.text}")
        else:
            print(f"Get upload link failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Sync error (to): {e}")
    return False

# --- CONFIG & DETECTION LOGIC ---

CONFIG_FILE = "config/keywords.json"
_CONFIG_CACHE = None

def load_config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE:
        return _CONFIG_CACHE
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                _CONFIG_CACHE = json.load(f)
                return _CONFIG_CACHE
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    return {}

def get_macro_category(cat: str) -> str:
    config = load_config()
    macro_map = config.get("macro_categories", {})
    for macro, subcats in macro_map.items():
        if cat in subcats:
            return macro
    return cat

def detect_category_granular(name_input: Union[str, Any], mapping: Optional[Dict[str, str]] = None) -> str:
    name = parsing_service.normalize_name(str(name_input))
    
    # 1. DYNAMIC MAPPING
    if mapping:
        if name in mapping:
            return mapping[name]
        raw_name = str(name_input)
        if raw_name in mapping:
             return mapping[raw_name]

    # 2. CONFIG KEYWORDS
    config = load_config()
    
    def check_keywords(text, keyword_list, exclusions=None):
        if not keyword_list: return False
        for k in keyword_list:
            if k in text:
                if exclusions:
                    if any(ex in text for ex in exclusions):
                        continue
                return True
        return False

    categories = config.get("categories", {})
    exclusions = config.get("exclusions", {})

    priority_order = [
         "🍔 Еда (Кухня)", "🍬 Доп. ингредиенты", "☕ Кофе", "🍵 Чай", 
         "🍓 Милк/Фреш/Смузи", "🧉 Коктейль Б/А", "🚰 Розлив Б/А", "🥤 Стекло/Банка Б/А",
         "🍏 Сидр ШТ", "🍾 Пиво ШТ", "🍺 Пиво Розлив", "🥃 Виски", "💧 Водка",
         "🏴‍☠️ Ром", "🌵 Текила", "🌲 Джин", "🍇 Коньяк/Бренди", "🍒 Ликер/Настойка",
         "🍷 Вино", "🍹 Коктейли"
    ]
    
    for cat_name in priority_order:
        keywords = categories.get(cat_name, [])
        cat_exclusions = exclusions.get(cat_name, [])
        if check_keywords(name, keywords, cat_exclusions):
            return cat_name

    return '📦 Прочее'

def apply_categories(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    if df is None or df.empty or "Блюдо" not in df.columns:
        return df
    cat_mapping = load_categories()
    df = df.copy()
    df['Категория'] = df['Блюдо'].apply(lambda x: detect_category_granular(x, cat_mapping))
    df['Макро_Категория'] = df['Категория'].apply(get_macro_category)
    return df
