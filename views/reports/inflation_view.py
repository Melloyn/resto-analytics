import streamlit as st
import pandas as pd
import ui
from services import analytics_service


@st.cache_data(show_spinner=False)
def _cached_prep_inflation_data(_df_full, _df_current, target_dt, start_dt, selection_signature, data_version):
    scope = _df_full[(_df_full['Дата_Отчета'] >= start_dt) & (_df_full['Дата_Отчета'] <= target_dt)]
    if scope.empty or _df_current.empty:
        return 0, 0, pd.DataFrame()
        
    old_prices = scope.sort_values('Дата_Отчета').groupby('Блюдо')['Unit_Cost'].first()
    current_prices = _df_current.groupby('Блюдо')['Unit_Cost'].mean()
    merged = pd.concat([old_prices, current_prices], axis=1, keys=['Old', 'New']).dropna()
    merged['Diff'] = merged['New'] - merged['Old']
    merged['Pct'] = (merged['Diff'] / merged['Old']) * 100
    merged = merged.replace([float('inf'), float('-inf')], pd.NA).dropna(subset=['Pct'])
    qty_map = _df_current.groupby('Блюдо')['Количество'].sum()
    merged['Qty'] = qty_map
    merged['Effect'] = merged['Diff'] * merged['Qty']
    loss = merged[merged['Effect'] > 0]['Effect'].sum()
    save = abs(merged[merged['Effect'] < 0]['Effect'].sum())
    det = merged[merged['Effect'] != 0].copy()
    det['Товар'] = det.index
    det['Рост %'] = det['Pct']
    det['Эффект (₽)'] = det['Effect']
    return loss, save, det

def render_inflation(df_full, df_current, target_date, inflation_start_date=None, selection_signature=None):
    data_version = st.session_state.get('data_version', 1)
    target_dt = pd.to_datetime(target_date)
    
    if True:
        if inflation_start_date is not None:
            start_dt = pd.to_datetime(inflation_start_date)
            loss, save, det = _cached_prep_inflation_data(df_full, df_current, target_dt, start_dt, selection_signature, data_version)
        else:
            loss, save, det = analytics_service.compute_inflation_metrics(df_full[df_full['Дата_Отчета'] <= target_dt], df_current)
    col1, col2, col3 = st.columns(3)
    col1.metric("🔴 Потери", f"-{loss:,.0f} ₽")
    col2.metric("🟢 Экономия", f"+{save:,.0f} ₽")
    net = save - loss
    col3.metric("Итог", f"{net:+,.0f} ₽")
    
    if not det.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Топ роста (Убыток)")
            ui.render_aggrid(det[det['Эффект (₽)'] > 0].sort_values('Эффект (₽)', ascending=False).head(20)[['Товар', 'Рост %', 'Эффект (₽)']], height=300, formatting={"Рост %": "%.1f %%", "Эффект (₽)": "%.0f ₽"})
        with c2:
            st.caption("Топ падения (Экономия)")
            ui.render_aggrid(det[det['Эффект (₽)'] < 0].sort_values('Эффект (₽)', ascending=True).head(20)[['Товар', 'Рост %', 'Эффект (₽)']], height=300, formatting={"Рост %": "%.1f %%", "Эффект (₽)": "%.0f ₽"})
