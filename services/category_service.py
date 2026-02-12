import json
import os
import requests
import streamlit as st

MAPPING_FILE = "categories.json"
YANDEX_MAPPING_PATH = "RestoAnalytic/config/categories.json"

DEFAULT_CATEGORIES = [
    "🍔 Еда (Кухня)", "🍹 Коктейли", "☕ Кофе", "🍵 Чай", "🍺 Пиво Розлив", "💧 Водка",
    "🍷 Вино", "🥤 Стекло/Банка Б/А", "🚰 Розлив Б/А", "🍓 Милк/Фреш/Смузи", 
    "🍏 Сидр ШТ", "🍾 Пиво ШТ", "🥃 Виски", "💧 Водка", "🏴‍☠️ Ром", 
    "🌵 Текила", "🌲 Джин", "🍇 Коньяк/Бренди", "🍒 Ликер/Настойка", "🍬 Доп. ингредиенты",
    "🧉 Коктейль Б/А", "📦 Прочее", "⛔ Исключить из отчетов"
]

def load_categories():
    """Load category mapping from local JSON."""
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_categories(new_map):
    """Save category mapping to local JSON."""
    current = load_categories()
    current.update(new_map)
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(current, f, ensure_ascii=False, indent=4)
        print("Updated categories saved.")
    return current

def save_categories_full(full_map):
    """Overwrite full category mapping JSON."""
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(full_map, f, ensure_ascii=False, indent=4)
    return full_map

def get_all_known_categories():
    """Return list of all unique categories (defaults + used in mapping)."""
    mapping = load_categories()
    cats = set(DEFAULT_CATEGORIES)
    if mapping:
        cats.update(mapping.values())
    return sorted(list(cats))

def sync_from_yandex(token, remote_path=YANDEX_MAPPING_PATH):
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
                with open(MAPPING_FILE, 'wb') as f:
                    f.write(dl.content)
                return True
    except Exception as e:
        print(f"Sync error: {e}")
    return False

def sync_to_yandex(token, remote_path=YANDEX_MAPPING_PATH):
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
                up = requests.put(href, files={'file': f})
                return up.status_code in [201, 202]
    except Exception as e:
        print(f"Sync error: {e}")
    return False
