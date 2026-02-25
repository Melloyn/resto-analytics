import pandas as pd
import numpy as np
from datetime import timedelta
from typing import List, Dict, Any, Tuple, Optional, Union
from use_cases.domain_models import InsightMetric

def calculate_insights(df_curr: pd.DataFrame, df_prev: pd.DataFrame, cur_rev: float, prev_rev: float, cur_fc: float) -> List[InsightMetric]:
    """
    Calculates business insights/alerts based on current and previous data.
    Returns a list of InsightMetric DTOs.
    Levels: 'success', 'warning', 'error', 'info'
    """
    insights = []
    
    # 1. Revenue Check
    if prev_rev > 0:
        rev_diff_pct = (cur_rev - prev_rev) / prev_rev * 100
        if rev_diff_pct < -10:
            insights.append(InsightMetric(
                type='rev_drop',
                message=f"📉 **Тревога по Выручке**: Падение на {abs(rev_diff_pct):.1f}% по сравнению с прошлым периодом.",
                level='error'
            ))
        elif rev_diff_pct > 20:
            insights.append(InsightMetric(
                type='rev_growth',
                message=f"🚀 **Отличный рост**: Выручка выросла на {rev_diff_pct:.1f}%!",
                level='success'
            ))

    # 2. Food Cost Check
    TARGET_FC = 35.0
    if cur_fc > TARGET_FC:
        insights.append(InsightMetric(
            type='high_fc',
            message=f"⚠️ **Высокий Фуд-кост**: Текущий {cur_fc:.1f}% (Цель: {TARGET_FC}%).",
            level='warning'
        ))
    
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
                insights.append(InsightMetric(
                    type='inflation',
                    message=f"💸 **Скачок цены**: {top_inflator} подорожал на {top_val:.0f}%.",
                    level='warning'
                ))

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
                insights.append(InsightMetric(
                    type='dogs',
                    message=f"🐶 **Мертвый груз**: Найдено {len(dogs)} позиций 'Собак' (мало продаж, мало денег).",
                    level='info'
                ))

    if not insights:
        insights.append(InsightMetric(
            type='all_good',
            message="✅ **Всё спокойно**: Критических отклонений не найдено.",
            level='success'
        ))

    return insights

def compute_inflation_metrics(df_scope: pd.DataFrame, df_v: pd.DataFrame) -> Tuple[float, float, pd.DataFrame]:
    if df_scope.empty or df_v.empty:
        return 0, 0, pd.DataFrame()
    last_prices = df_scope.sort_values('Дата_Отчета').groupby('Блюдо')['Unit_Cost'].last()
    current_prices = df_v.groupby('Блюдо')['Unit_Cost'].mean()

    merged = pd.concat([last_prices, current_prices], axis=1, keys=['Old', 'New']).dropna()
    merged['Diff'] = merged['New'] - merged['Old']
    merged['Pct'] = (merged['Diff'] / merged['Old']) * 100

    qty_map = df_v.groupby('Блюдо')['Количество'].sum()
    merged['Qty'] = qty_map
    merged['Effect'] = merged['Diff'] * merged['Qty']

    loss = merged[merged['Effect'] > 0]['Effect'].sum()
    save = abs(merged[merged['Effect'] < 0]['Effect'].sum())

    detail = merged[merged['Effect'] != 0].copy()
    detail['Товар'] = detail.index
    detail['Рост %'] = detail['Pct']
    detail['Эффект (₽)'] = detail['Effect']
    return loss, save, detail


def compute_supplier_stats(df: pd.DataFrame) -> pd.DataFrame:
    if 'Поставщик' not in df.columns or df.empty:
        return pd.DataFrame()
    return (
        df.groupby('Поставщик')['Себестоимость']
        .sum()
        .reset_index()
        .sort_values('Себестоимость', ascending=False)
        .head(15)
    )


def compute_menu_tab_data(df: pd.DataFrame, group_col: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    cat_df = (
        df.groupby(group_col)['Выручка с НДС']
        .sum()
        .reset_index()
        .sort_values(by='Выручка с НДС', ascending=False)
    )

    menu_df = df.groupby('Блюдо').agg({
        'Выручка с НДС': 'sum',
        'Себестоимость': 'sum',
        'Количество': 'sum'
    }).reset_index()
    menu_df['Фудкост %'] = (menu_df['Себестоимость'] / menu_df['Выручка с НДС'] * 100).fillna(0)
    menu_df = menu_df.sort_values('Выручка с НДС', ascending=False)
    return cat_df, menu_df


def compute_abc_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, float, float]:
    if df.empty:
        return pd.DataFrame(), 0, 0
    abc = df.groupby('Блюдо').agg({
        'Выручка с НДС': 'sum',
        'Количество': 'sum',
        'Себестоимость': 'sum'
    }).reset_index()
    abc['Margin'] = abc['Выручка с НДС'] - abc['Себестоимость']
    abc['Unit_Margin'] = abc['Margin'] / abc['Количество']

    avg_qty = abc['Количество'].mean()
    avg_margin = abc['Unit_Margin'].mean()

    def classify(row):
        high_vol = row['Количество'] >= avg_qty
        high_prof = row['Unit_Margin'] >= avg_margin
        if high_vol and high_prof:
            return "⭐ Звезда"
        if high_vol and not high_prof:
            return "🐎 Лошадка"
        if not high_vol and high_prof:
            return "❓ Загадка"
        return "🐶 Собака"

    abc['Класс'] = abc.apply(classify, axis=1)
    return abc, avg_qty, avg_margin


def compute_weekday_stats(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    ru_days = {
        0: 'Понедельник', 1: 'Вторник', 2: 'Среда', 3: 'Четверг',
        4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
    }

    daily = df.groupby('Дата_Отчета')['Выручка с НДС'].sum().reset_index()
    daily['ДеньРус'] = daily['Дата_Отчета'].dt.weekday.map(ru_days)
    daily['Дата_Подпись'] = daily['Дата_Отчета'].dt.strftime('%d.%m')

    dates_per_weekday = df[['Дата_Отчета']].drop_duplicates()
    dates_per_weekday['Day'] = dates_per_weekday['Дата_Отчета'].dt.weekday.map(ru_days)
    counts = dates_per_weekday['Day'].value_counts()

    sums = df.groupby(df['Дата_Отчета'].dt.weekday.map(ru_days))['Выручка с НДС'].sum()
    avgs = (sums / counts).rename('Выручка с НДС').rename_axis('ДеньРус').reset_index()

    days_order = {
        'Понедельник': 0, 'Вторник': 1, 'Среда': 2, 'Четверг': 3,
        'Пятница': 4, 'Суббота': 5, 'Воскресенье': 6
    }
    avgs['SortKey'] = avgs['ДеньРус'].map(days_order)
    avgs = avgs.sort_values('SortKey').drop(columns=['SortKey'])

    return daily, avgs


def compute_purchase_plan(df: pd.DataFrame, days: int, safety: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=['Budget'])
    end_dt = df['Дата_Отчета'].max()
    start_dt = end_dt - timedelta(days=30)
    recent = df[df['Дата_Отчета'] >= start_dt]

    daily_usage = recent.groupby('Блюдо')['Количество'].sum() / 30
    last_cost = recent.sort_values('Дата_Отчета').groupby('Блюдо')['Unit_Cost'].last()

    plan = pd.DataFrame({'Daily_Use': daily_usage, 'Unit_Cost': last_cost}).dropna()
    plan['Need_Qty'] = plan['Daily_Use'] * days * (1 + safety/100)
    plan['Budget'] = plan['Need_Qty'] * plan['Unit_Cost']

    return plan.sort_values('Budget', ascending=False).reset_index()


def compute_simulation(df: pd.DataFrame, cats: List[str], d_price: float, d_cost: float, d_vol: float) -> Optional[Dict[str, float]]:
    if df.empty:
        return None
    mask = df['Категория'].isin(cats)
    target = df[mask].copy()
    other = df[~mask].copy()

    base_rev = df['Выручка с НДС'].sum()
    base_cost = df['Себестоимость'].sum()
    base_margin = base_rev - base_cost

    sim_rev_target = target['Выручка с НДС'].sum() * (1 + d_price/100) * (1 + d_vol/100)
    sim_cost_target = target['Себестоимость'].sum() * (1 + d_cost/100) * (1 + d_vol/100)

    sim_rev = other['Выручка с НДС'].sum() + sim_rev_target
    sim_cost = other['Себестоимость'].sum() + sim_cost_target
    sim_margin = sim_rev - sim_cost

    return {
        'base_revenue': base_rev,
        'base_margin': base_margin,
        'sim_revenue': sim_rev,
        'sim_margin': sim_margin,
        'diff_rev': sim_rev - base_rev,
        'diff_margin': sim_margin - base_margin,
        'old_profitability': (base_margin / base_rev * 100) if base_rev else 0,
        'new_profitability': (sim_margin / sim_rev * 100) if sim_rev else 0
    }

def get_unique_ingredients(recipes_db: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """
    Extracts a sorted list of unique ingredient names from the recipes database.
    """
    ingredients = set()
    for dish_ingredients in recipes_db.values():
        for ing in dish_ingredients:
            if ing.get('ingredient'):
                ingredients.add(ing['ingredient'])
    return sorted(list(ingredients))

def simulate_forecast(
    recipes_db: Dict[str, List[Dict[str, Any]]],
    ingredient_deltas: Dict[str, float],
    df_current: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculates the impact of ingredient price changes on dish unit costs.
    
    Args:
        recipes_db: Dictionary of recipes {dish_name: [{'ingredient': name, 'qty_per_dish': qty}, ...]}
        ingredient_deltas: Dictionary of price increases per unit {ingredient_name: price_increase_rub}
        df_current: DataFrame containing current dish data (must have 'Блюдо', 'Unit_Cost', 'Количество')
        
    Returns:
        DataFrame with columns: ['Блюдо', 'Текущая с/с', 'Рост с/с', 'Новая с/с', 'Количество']
    """
    if not recipes_db or not ingredient_deltas or df_current.empty:
        return pd.DataFrame()

    dish_impacts = {}

    # 1. Calculate impact per dish based on recipes
    for dish_name, ingredients in recipes_db.items():
        # Recipe dish names are typically normalized (lowercase) by parsing_service
        # But we ensure it here just in case
        norm_dish = str(dish_name).lower().strip()
        
        impact = 0.0
        for ing in ingredients:
            ing_name = ing.get('ingredient') # normalized by parsing_service
            qty = ing.get('qty_per_dish', 0)
            
            # check if this ingredient has a price increase
            if ing_name in ingredient_deltas:
                delta = ingredient_deltas[ing_name]
                impact += qty * delta
        
        if impact > 0:
            dish_impacts[norm_dish] = impact

    if not dish_impacts:
        return pd.DataFrame()

    # 2. Map impact to existing dishes in DataFrame
    # Create a normalized lookup column for sales data
    df_work = df_current.copy()
    df_work['dish_norm'] = df_work['Блюдо'].astype(str).str.lower().str.strip()
    
    # Filter only relevant dishes using normalized names
    affected_mask = df_work['dish_norm'].isin(dish_impacts.keys())
    affected_dishes = df_work[affected_mask].copy()
    
    if affected_dishes.empty:
        return pd.DataFrame()
        
    results = []
    
    for _, row in affected_dishes.iterrows():
        dish_display = row['Блюдо']
        dish_norm = row['dish_norm']
        
        current_cost = row.get('Unit_Cost', 0)
        # Look up impact using normalized key
        impact = dish_impacts.get(dish_norm, 0)
        
        new_cost = current_cost + impact
        qty = row.get('Количество', 0)
        
        results.append({
            'Блюдо': dish_display,
            'Текущая с/с': current_cost,
            'Рост с/с': impact,
            'Новая с/с': new_cost,
            'Количество': qty
        })
        
    return pd.DataFrame(results)
