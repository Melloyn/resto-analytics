import json
import os
import requests
import pandas as pd
import logging
from typing import List, Dict, Any, Optional, Union
from services import parsing_service

log = logging.getLogger(__name__)

MAPPING_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "categories.json")
YANDEX_MAPPING_PATH = "RestoAnalytic/categories.json"

DEFAULT_CATEGORIES = [
    "🍔 Еда (Кухня)", "![Cocktail](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4gIDxkZWZzPiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImdsQmFzZSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+ICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iIzJhMmEyYSIgc3RvcC1vcGFjaXR5PSIwLjgiLz4gICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwNTA1MDUiIHN0b3Atb3BhY2l0eT0iMC45Ii8+ICAgIDwvbGluZWFyR3JhZGllbnQ+ICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ2xIaWdobGlnaHQiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4gICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMyIvPiAgICAgIDxzdG9wIG9mZnNldD0iNTAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMCIvPiAgICA8L2xpbmVhckdyYWRpZW50PiAgICA8ZmlsdGVyIGlkPSJnbG93ZmYwMDg4IiB4PSItMjAlIiB5PSItMjAlIiB3aWR0aD0iMTQwJSIgaGVpZ2h0PSIxNDAlIj4gICAgICA8ZmVHYXVzc2lhbkJsdXIgc3RkRGV2aWF0aW9uPSIzIiByZXN1bHQ9ImJsdXIiIC8+ICAgICAgPGZlQ29tcG9zaXRlIGluPSJTb3VyY2VHcmFwaGljIiBpbjI9ImJsdXIiIG9wZXJhdG9yPSJvdmVyIiAvPiAgICA8L2ZpbHRlcj4gIDwvZGVmcz4gICAgPCEtLSBPdXRlciBnbGFzcyBib3VuZGFyeSAmIGRyb3Agc2hhZG93IC0tPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xCYXNlKSIvPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xIaWdobGlnaHQpIi8+ICAgIDwhLS0gR2xhc3MgaW5uZXIgcmltICh0b3AgcmltIGhpZ2hsaWdodCB0byBtYWtlIGl0IDNEKSAtLT4gIDxwYXRoIGQ9Ik0gMTYsNCBMIDQ4LDQgQyA1NSw0IDYwLDkgNjAsMTYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgPCEtLSBHbGFzcyBib3R0b20gcmltIHJlZmxlY3Rpb24gLS0+ICA8cGF0aCBkPSJNIDQsNDggQyA0LDU1IDksNjAgMTYsNjAgTCA0OCw2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utb3BhY2l0eT0iMC4xIiBzdHJva2Utd2lkdGg9IjEiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgICA8IS0tIElubmVyIEljb24gQ2VudGVyZWQgLS0+ICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxNiwgMTYpIHNjYWxlKDEuMzMzKSI+ICAgIDxnIGZpbHRlcj0idXJsKCNnbG93ZmYwMDg4KSIgc3Ryb2tlPSIjZmYwMDg4IiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPHBhdGggZD0iTTggMjJoOCIvPjxwYXRoIGQ9Ik0xMiAxMXYxMSIvPjxwYXRoIGQ9Im0xOSAzLTcgOC03LThaIi8+ICAgIDwvZz4gICAgPCEtLSBTaGFycCB3aGl0ZSBjb3JlIGZvciB0aGUgbmVvbiB0dWJlIGVmZmVjdCAtLT4gICAgPGcgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjEiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPHBhdGggZD0iTTggMjJoOCIvPjxwYXRoIGQ9Ik0xMiAxMXYxMSIvPjxwYXRoIGQ9Im0xOSAzLTcgOC03LThaIi8+ICAgIDwvZz4gIDwvZz48L3N2Zz4=) Коктейли", "![Coffee](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4gIDxkZWZzPiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImdsQmFzZSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+ICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iIzJhMmEyYSIgc3RvcC1vcGFjaXR5PSIwLjgiLz4gICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwNTA1MDUiIHN0b3Atb3BhY2l0eT0iMC45Ii8+ICAgIDwvbGluZWFyR3JhZGllbnQ+ICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ2xIaWdobGlnaHQiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4gICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMyIvPiAgICAgIDxzdG9wIG9mZnNldD0iNTAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMCIvPiAgICA8L2xpbmVhckdyYWRpZW50PiAgICA8ZmlsdGVyIGlkPSJnbG93ZmZhYTAwIiB4PSItMjAlIiB5PSItMjAlIiB3aWR0aD0iMTQwJSIgaGVpZ2h0PSIxNDAlIj4gICAgICA8ZmVHYXVzc2lhbkJsdXIgc3RkRGV2aWF0aW9uPSIzIiByZXN1bHQ9ImJsdXIiIC8+ICAgICAgPGZlQ29tcG9zaXRlIGluPSJTb3VyY2VHcmFwaGljIiBpbjI9ImJsdXIiIG9wZXJhdG9yPSJvdmVyIiAvPiAgICA8L2ZpbHRlcj4gIDwvZGVmcz4gICAgPCEtLSBPdXRlciBnbGFzcyBib3VuZGFyeSAmIGRyb3Agc2hhZG93IC0tPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xCYXNlKSIvPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xIaWdobGlnaHQpIi8+ICAgIDwhLS0gR2xhc3MgaW5uZXIgcmltICh0b3AgcmltIGhpZ2hsaWdodCB0byBtYWtlIGl0IDNEKSAtLT4gIDxwYXRoIGQ9Ik0gMTYsNCBMIDQ4LDQgQyA1NSw0IDYwLDkgNjAsMTYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgPCEtLSBHbGFzcyBib3R0b20gcmltIHJlZmxlY3Rpb24gLS0+ICA8cGF0aCBkPSJNIDQsNDggQyA0LDU1IDksNjAgMTYsNjAgTCA0OCw2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utb3BhY2l0eT0iMC4xIiBzdHJva2Utd2lkdGg9IjEiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgICA8IS0tIElubmVyIEljb24gQ2VudGVyZWQgLS0+ICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxNiwgMTYpIHNjYWxlKDEuMzMzKSI+ICAgIDxnIGZpbHRlcj0idXJsKCNnbG93ZmZhYTAwKSIgc3Ryb2tlPSIjZmZhYTAwIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPHBhdGggZD0iTTE4IDhoMWE0IDQgMCAwIDEgMCA4aC0xIi8+PHBhdGggZD0iTTIgOGgxNnY5YTQgNCAwIDAgMS00IDRINmE0IDQgMCAwIDEtNC00Vjh6Ii8+PGxpbmUgeDE9IjYiIHkxPSIxIiB4Mj0iNiIgeTI9IjQiLz48bGluZSB4MT0iMTAiIHkxPSIxIiB4Mj0iMTAiIHkyPSI0Ii8+PGxpbmUgeDE9IjE0IiB5MT0iMSIgeDI9IjE0IiB5Mj0iNCIvPiAgICA8L2c+ICAgIDwhLS0gU2hhcnAgd2hpdGUgY29yZSBmb3IgdGhlIG5lb24gdHViZSBlZmZlY3QgLS0+ICAgIDxnIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLXdpZHRoPSIxIiBmaWxsPSJub25lIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPiAgICAgIDxwYXRoIGQ9Ik0xOCA4aDFhNCA0IDAgMCAxIDAgOGgtMSIvPjxwYXRoIGQ9Ik0yIDhoMTZ2OWE0IDQgMCAwIDEtNCA0SDZhNCA0IDAgMCAxLTQtNFY4eiIvPjxsaW5lIHgxPSI2IiB5MT0iMSIgeDI9IjYiIHkyPSI0Ii8+PGxpbmUgeDE9IjEwIiB5MT0iMSIgeDI9IjEwIiB5Mj0iNCIvPjxsaW5lIHgxPSIxNCIgeTE9IjEiIHgyPSIxNCIgeTI9IjQiLz4gICAgPC9nPiAgPC9nPjwvc3ZnPg==) Кофе", "🍵 Чай", "![Beer](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4gIDxkZWZzPiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImdsQmFzZSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+ICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iIzJhMmEyYSIgc3RvcC1vcGFjaXR5PSIwLjgiLz4gICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwNTA1MDUiIHN0b3Atb3BhY2l0eT0iMC45Ii8+ICAgIDwvbGluZWFyR3JhZGllbnQ+ICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ2xIaWdobGlnaHQiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4gICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMyIvPiAgICAgIDxzdG9wIG9mZnNldD0iNTAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMCIvPiAgICA8L2xpbmVhckdyYWRpZW50PiAgICA8ZmlsdGVyIGlkPSJnbG93ZmZlZTAwIiB4PSItMjAlIiB5PSItMjAlIiB3aWR0aD0iMTQwJSIgaGVpZ2h0PSIxNDAlIj4gICAgICA8ZmVHYXVzc2lhbkJsdXIgc3RkRGV2aWF0aW9uPSIzIiByZXN1bHQ9ImJsdXIiIC8+ICAgICAgPGZlQ29tcG9zaXRlIGluPSJTb3VyY2VHcmFwaGljIiBpbjI9ImJsdXIiIG9wZXJhdG9yPSJvdmVyIiAvPiAgICA8L2ZpbHRlcj4gIDwvZGVmcz4gICAgPCEtLSBPdXRlciBnbGFzcyBib3VuZGFyeSAmIGRyb3Agc2hhZG93IC0tPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xCYXNlKSIvPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xIaWdobGlnaHQpIi8+ICAgIDwhLS0gR2xhc3MgaW5uZXIgcmltICh0b3AgcmltIGhpZ2hsaWdodCB0byBtYWtlIGl0IDNEKSAtLT4gIDxwYXRoIGQ9Ik0gMTYsNCBMIDQ4LDQgQyA1NSw0IDYwLDkgNjAsMTYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgPCEtLSBHbGFzcyBib3R0b20gcmltIHJlZmxlY3Rpb24gLS0+ICA8cGF0aCBkPSJNIDQsNDggQyA0LDU1IDksNjAgMTYsNjAgTCA0OCw2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utb3BhY2l0eT0iMC4xIiBzdHJva2Utd2lkdGg9IjEiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgICA8IS0tIElubmVyIEljb24gQ2VudGVyZWQgLS0+ICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxNiwgMTYpIHNjYWxlKDEuMzMzKSI+ICAgIDxnIGZpbHRlcj0idXJsKCNnbG93ZmZlZTAwKSIgc3Ryb2tlPSIjZmZlZTAwIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPHBhdGggZD0ibTYgOCAxLjc1IDEyLjI4QTIgMiAwIDAgMCA5Ljc0IDIyaDQuNTJhMiAyIDAgMCAwIDEuOTktMS43MkwxOCA4Ii8+PHBhdGggZD0iTTUgOGgxNCIvPjxwYXRoIGQ9Ik03IDUgNiA4Ii8+PHBhdGggZD0iTTE3IDUgMTggOCIvPjxwYXRoIGQ9Ik0xMiA1VjIiLz4gICAgPC9nPiAgICA8IS0tIFNoYXJwIHdoaXRlIGNvcmUgZm9yIHRoZSBuZW9uIHR1YmUgZWZmZWN0IC0tPiAgICA8ZyBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMSIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj4gICAgICA8cGF0aCBkPSJtNiA4IDEuNzUgMTIuMjhBMiAyIDAgMCAwIDkuNzQgMjJoNC41MmEyIDIgMCAwIDAgMS45OS0xLjcyTDE4IDgiLz48cGF0aCBkPSJNNSA4aDE0Ii8+PHBhdGggZD0iTTcgNSA2IDgiLz48cGF0aCBkPSJNMTcgNSAxOCA4Ii8+PHBhdGggZD0iTTEyIDVWMiIvPiAgICA8L2c+ICA8L2c+PC9zdmc+) Пиво Розлив", "💧 Водка",
    "🍷 Вино", "�� Стекло/Банка Б/А", "🚰 Розлив Б/А", "🍓 Милк/Фреш/Смузи", 
    "🍏 Сидр ШТ", "🍾 Пиво ШТ", "🥃 Виски", "🏴‍☠️ Ром", 
    "🌵 Текила", "🌲 Джин", "🍇 Коньяк/Бренди", "🍒 Ликер/Настойка", "🍬 Доп. ингредиенты",
    "🧉 Коктейль Б/А", "📦 Прочее", "⛔ Исключить из отчетов"
](https://cdn-icons-png.flaticon.com/128/10427/10427184.png) Коктейли", "![Coffee](https://cdn-icons-png.flaticon.com/128/9336/9336100.png) Кофе", "🍵 Чай", "![Beer](https://cdn-icons-png.flaticon.com/128/9643/9643446.png) Пиво Розлив", "💧 Водка",
    "🍷 Вино", "🥤 Стекло/Банка Б/А", "🚰 Розлив Б/А", "🍓 Милк/Фреш/Смузи", 
    "🍏 Сидр ШТ", "🍾 Пиво ШТ", "🥃 Виски", "🏴‍☠️ Ром", 
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
            log.error(f"Error loading categories: {e}")
            return {}
    return {}

def save_categories(new_map: Dict[str, str]) -> Dict[str, str]:
    """Save category mapping to local JSON."""
    current = load_categories()
    current.update(new_map)
    try:
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=4)
            log.info(f"Updated categories saved to {MAPPING_FILE}")
    except Exception as e:
        log.error(f"Error saving categories: {e}")
    return current

def save_categories_full(full_map: Dict[str, str]) -> Dict[str, str]:
    """Overwrite full category mapping JSON."""
    try:
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(full_map, f, ensure_ascii=False, indent=4)
    except Exception as e:
        log.error(f"Error saving full categories: {e}")
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
                        log.error("Failed to parse remote JSON")
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
                log.info("Synced from Yandex successfully.")
                return True
        elif resp.status_code == 404:
            # Remote file doesn't exist yet, that's fine, keep local
            log.warning("Remote categories not found (404).")
            return True
    except Exception as e:
        log.error(f"Sync error (from): {e}", exc_info=True)
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
                    log.info("Synced to Yandex successfully.")
                    return True
                else:
                    log.error(f"Upload failed: {up.status_code} {up.text}")
        else:
            log.error(f"Get upload link failed: {resp.status_code} {resp.text}")
    except Exception as e:
        log.error(f"Sync error (to): {e}", exc_info=True)
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
            log.error(f"Error loading config: {e}")
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
