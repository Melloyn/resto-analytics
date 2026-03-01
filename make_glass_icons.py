import base64
import json
import re
import os

def create_glass_icon_b64(path_content, color):
    # This SVG carefully mimics a dark 3D glass app icon with a glowing glowing symbol inside.
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="glBase" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2a2a2a" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#050505" stop-opacity="0.9"/>
    </linearGradient>
    <linearGradient id="glHighlight" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.3"/>
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.0"/>
    </linearGradient>
    <filter id="glow{color.strip('#')}" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>
  
  <!-- Outer glass boundary & drop shadow -->
  <rect x="4" y="4" width="56" height="56" rx="14" fill="url(#glBase)"/>
  <rect x="4" y="4" width="56" height="56" rx="14" fill="url(#glHighlight)"/>
  
  <!-- Glass inner rim (top rim highlight to make it 3D) -->
  <path d="M 16,4 L 48,4 C 55,4 60,9 60,16" fill="none" stroke="#ffffff" stroke-opacity="0.4" stroke-width="1.5" stroke-linecap="round"/>
  <!-- Glass bottom rim reflection -->
  <path d="M 4,48 C 4,55 9,60 16,60 L 48,60" fill="none" stroke="#ffffff" stroke-opacity="0.1" stroke-width="1" stroke-linecap="round"/>
  
  <!-- Inner Icon Centered -->
  <g transform="translate(16, 16) scale(1.333)">
    <g filter="url(#glow{color.strip('#')})" stroke="{color}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
      {path_content}
    </g>
    <!-- Sharp white core for the neon tube effect -->
    <g stroke="#ffffff" stroke-width="1" fill="none" stroke-linecap="round" stroke-linejoin="round">
      {path_content}
    </g>
  </g>
</svg>"""
    svg = svg.replace('\n', '')
    b64 = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{b64}"

ICONS = {
    "revenue": create_glass_icon_b64('<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>', "#ffcc00"),
    "inflation": create_glass_icon_b64('<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>', "#ff3333"),
    "abc": create_glass_icon_b64('<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>', "#00ff88"),
    "simulator": create_glass_icon_b64('<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>', "#ff9900"),
    "weekdays": create_glass_icon_b64('<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>', "#cc66ff"),
    "procurement": create_glass_icon_b64('<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>', "#00ccff"),
    "cocktail": create_glass_icon_b64('<path d="M8 22h8"/><path d="M12 11v11"/><path d="m19 3-7 8-7-8Z"/>', "#ff0088"),
    "coffee": create_glass_icon_b64('<path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/>', "#ffaa00"),
    "beer": create_glass_icon_b64('<path d="m6 8 1.75 12.28A2 2 0 0 0 9.74 22h4.52a2 2 0 0 0 1.99-1.72L18 8"/><path d="M5 8h14"/><path d="M7 5 6 8"/><path d="M17 5 18 8"/><path d="M12 5V2"/>', "#ffee00")
}

# 1. Update report_flow.py
rf_path = "use_cases/report_flow.py"
with open(rf_path, "r", encoding="utf-8") as f:
    rf_content = f.read()

mapping = {
    0: f'    "![Rev]({ICONS["revenue"]}) Выручка",',
    1: f'    "![Inf]({ICONS["inflation"]}) Инфляция С/С",',
    2: f'    "![ABC]({ICONS["abc"]}) ABC-анализ",',
    3: f'    "![Sim]({ICONS["simulator"]}) Симулятор",',
    4: f'    "![Days]({ICONS["weekdays"]}) Дни недели",',
    5: f'    "![Proc]({ICONS["procurement"]}) Закупки",'
}

start_str = "REPORT_TAB_LABELS: Tuple[str, ...] = ("
if start_str in rf_content:
    head, tail = rf_content.split(start_str, 1)
    block, rest = tail.split(")", 1)
    new_block = "\n" + "\n".join(mapping.values()) + "\n"
    rf_content = head + start_str + new_block + ")" + rest

with open(rf_path, "w", encoding="utf-8") as f:
    f.write(rf_content)

# 2. Update category_service.py
cs_path = "services/category_service.py"
with open(cs_path, "r", encoding="utf-8") as f:
    cs_content = f.read()

cat_block_start = "DEFAULT_CATEGORIES = ["
if cat_block_start in cs_content:
    head, tail = cs_content.split(cat_block_start, 1)
    block, rest = tail.split("]", 1)
    # We rebuild the array string
    new_block = f"""
    "🍔 Еда (Кухня)", "![Cocktail]({ICONS["cocktail"]}) Коктейли", "![Coffee]({ICONS["coffee"]}) Кофе", "🍵 Чай", "![Beer]({ICONS["beer"]}) Пиво Розлив", "💧 Водка",
    "🍷 Вино", "�� Стекло/Банка Б/А", "🚰 Розлив Б/А", "🍓 Милк/Фреш/Смузи", 
    "🍏 Сидр ШТ", "🍾 Пиво ШТ", "🥃 Виски", "🏴‍☠️ Ром", 
    "🌵 Текила", "🌲 Джин", "🍇 Коньяк/Бренди", "🍒 Ликер/Настойка", "🍬 Доп. ингредиенты",
    "🧉 Коктейль Б/А", "📦 Прочее", "⛔ Исключить из отчетов"
"""
    cs_content = head + cat_block_start + new_block + "]" + rest

with open(cs_path, "w", encoding="utf-8") as f:
    f.write(cs_content)

# 3. Update categories.json
json_path = "categories.json"
with open(json_path, "r", encoding="utf-8") as f:
    cat_data = json.load(f)

for k, v in cat_data.items():
    if "Коктейли" in v:
        cat_data[k] = f"![Cocktail]({ICONS['cocktail']}) Коктейли"
    elif "Кофе" in v:
        cat_data[k] = f"![Coffee]({ICONS['coffee']}) Кофе"
    elif "Пиво Розлив" in v:
        cat_data[k] = f"![Beer]({ICONS['beer']}) Пиво Розлив"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(cat_data, f, ensure_ascii=False, indent=4)

print("Icons perfectly updated.")
