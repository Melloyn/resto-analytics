import streamlit as st
import ui

def render_kpi(df_current, df_prev, period_title):
    placeholder = st.empty()
    with placeholder.container():
        ui.render_skeleton_kpis(num_cols=4)
        import time; time.sleep(0.01)

    cur_rev = df_current['Выручка с НДС'].sum()
    cur_cost = df_current['Себестоимость'].sum()
    cur_fc = (cur_cost / cur_rev * 100) if cur_rev else 0
    cur_margin = cur_rev - cur_cost
    
    prev_rev = 0
    prev_fc = 0
    prev_margin = 0
    if not df_prev.empty:
        prev_rev = df_prev['Выручка с НДС'].sum()
        prev_cost = df_prev['Себестоимость'].sum()
        prev_fc = (prev_cost / prev_rev * 100) if prev_rev else 0
        prev_margin = prev_rev - prev_cost
    
    placeholder.empty()
    st.write(f"### 📊 Сводка: {period_title}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Выручка", f"{cur_rev:,.0f} ₽", f"{cur_rev - prev_rev:+,.0f} ₽" if not df_prev.empty else None)
    c2.metric("📉 Фуд-кост", f"{cur_fc:.1f} %", f"{cur_fc - prev_fc:+.1f} %" if not df_prev.empty else None, delta_color="inverse")
    c3.metric("💳 Маржа", f"{cur_margin:,.0f} ₽", f"{cur_margin - prev_margin:+,.0f} ₽" if not df_prev.empty else None)
    c4.metric("🧾 Позиций", len(df_current))
