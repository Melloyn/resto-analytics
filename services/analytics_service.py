import pandas as pd
import numpy as np
from typing import List, Dict, Any, Union

def calculate_insights(df_curr: pd.DataFrame, df_prev: pd.DataFrame, cur_rev: float, prev_rev: float, cur_fc: float) -> List[Dict[str, str]]:
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
