import streamlit as st
import plotly.express as px
import pandas as pd
import ui
from services import analytics_service

def render_dynamics(df_full, df_current):
    c1, c2 = st.columns([2, 1])
    with c1:
        st.write("### Динамика цены закупки")
        all_items = sorted(df_full['Блюдо'].unique())
        if all_items:
            sel = st.selectbox("Товар:", all_items)
            trend = df_full[df_full['Блюдо'] == sel].sort_values('Дата_Отчета')
            fig = px.line(trend, x='Дата_Отчета', y='Unit_Cost', title=f"Цена: {sel}", markers=True)
            st.plotly_chart(ui.update_chart_layout(fig), use_container_width=True)
    with c2:
        st.write("### Топ Поставщиков")
        stats = analytics_service.compute_supplier_stats(df_current)
        if not stats.empty:
            fig = px.bar(stats, x='Себестоимость', y='Поставщик', orientation='h')
            st.plotly_chart(ui.update_chart_layout(fig), use_container_width=True)

def render_menu(df_current, df_prev, current_label="", prev_label=""):
    placeholder = st.empty()
    with placeholder.container():
        ui.render_skeleton_chart()
        import time; time.sleep(0.01)

    view_mode = st.radio("Вид:", ["Макро", "Микро"], horizontal=True, label_visibility="collapsed")
    target_cat = 'Макро_Категория' if view_mode == "Макро" else 'Категория'
    
    cats, items = analytics_service.compute_menu_tab_data(df_current, target_cat)
    
    placeholder.empty()
    c1, c2 = st.columns([1, 1.5])
    with c1:
        # Clean donut: group small categories into "Прочее" and simplify legend
        cats_sorted = cats.sort_values('Выручка с НДС', ascending=False).copy()
        total_rev = cats_sorted['Выручка с НДС'].sum()
        if total_rev > 0:
            cats_sorted['share'] = cats_sorted['Выручка с НДС'] / total_rev
            # Increased threshold to avoid clutter
            small_mask = cats_sorted['share'] < 0.05
            if small_mask.any():
                other_sum = cats_sorted.loc[small_mask, 'Выручка с НДС'].sum()
                cats_sorted = cats_sorted.loc[~small_mask, [target_cat, 'Выручка с НДС']]
                cats_sorted = pd.concat(
                    [cats_sorted, pd.DataFrame({target_cat: ["🔹 Остальное (мелкое)"], "Выручка с НДС": [other_sum]})],
                    ignore_index=True
                )
        
        fig = px.pie(
            cats_sorted,
            values='Выручка с НДС',
            names=target_cat,
            hole=0.5,
            title="Структура выручки"
        )
        # Apply global theme first
        fig = ui.update_chart_layout(fig)
        
        # Then override for specific pie chart needs
        fig.update_traces(
            textposition='auto', 
            textinfo='percent',
            pull=[0.05] + [0] * (len(cats_sorted)-1)
        )
        
        # Legend on the right (vertical) looks cleaner for many items
        fig.update_layout(
            legend=dict(
                orientation="v", 
                yanchor="top", 
                y=1, 
                xanchor="left", 
                x=1.05
            ),
            title=dict(x=0.05, y=0.98, xanchor="left", yanchor="top"),
            margin=dict(l=20, r=120, t=60, b=20),
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        if not df_current.empty:
            with st.expander("🔍 Фильтр таблицы фудкоста", expanded=False):
                c_f1, c_f2 = st.columns(2)
                with c_f1:
                    min_rev = st.number_input("Мин. выручка (₽)", min_value=0, value=0, step=1000)
                    min_qty = st.number_input("Мин. кол-во", min_value=0, value=0, step=10)
                with c_f2:
                    top_n = st.slider("Показать топ N по выручке", 10, 300, 150)

            period_sorted = df_current.sort_values('Дата_Отчета')
            cost_start = period_sorted.groupby('Блюдо')['Unit_Cost'].first()
            cost_end = period_sorted.groupby('Блюдо')['Unit_Cost'].last()
            agg = df_current.groupby('Блюдо').agg({
                'Выручка с НДС': 'sum',
                'Себестоимость': 'sum',
                'Количество': 'sum'
            })
            agg['Факт фудкост %'] = (agg['Себестоимость'] / agg['Выручка с НДС'] * 100).fillna(0)
            agg = agg[(agg['Выручка с НДС'] >= min_rev) & (agg['Количество'] >= min_qty)]
            df_fc = pd.DataFrame({
                'Блюдо': agg.index,
                'С/С начало периода': cost_start,
                'С/С конец периода': cost_end,
                'Факт фудкост %': agg['Факт фудкост %'],
                'Выручка с НДС': agg['Выручка с НДС'],
                'Кол-во продано': agg['Количество']
            }).reset_index(drop=True)
            df_fc = df_fc.sort_values('Выручка с НДС', ascending=False).head(top_n)
            ui.render_aggrid(
                df_fc,
                height=500,
                pagination=True,
                formatting={
                    "С/С начало периода": "%.2f ₽",
                    "С/С конец периода": "%.2f ₽",
                    "Факт фудкост %": "%.1f %%",
                    "Выручка с НДС": "%.0f ₽",
                    "Кол-во продано": "%.0f"
                }
            )
        else:
            st.info("Нет данных для расчета фудкоста.")

    if not df_prev.empty:
        cats_prev, _ = analytics_service.compute_menu_tab_data(df_prev, target_cat)
        cur_cmp = cats.rename(columns={'Выручка с НДС': 'Текущий'})
        prev_cmp = cats_prev.rename(columns={'Выручка с НДС': 'Сравнение'})
        cmp_df = cur_cmp.merge(prev_cmp, on=target_cat, how='outer').fillna(0)
        cmp_df = cmp_df.sort_values('Текущий', ascending=False).head(12)
        cmp_long = cmp_df.melt(
            id_vars=[target_cat],
            value_vars=['Текущий', 'Сравнение'],
            var_name='Период',
            value_name='Выручка с НДС'
        )
        period_names = {
            'Текущий': current_label or 'Текущий период',
            'Сравнение': prev_label or 'Период сравнения',
        }
        cmp_long['Период'] = cmp_long['Период'].map(period_names)
        fig_cmp = px.bar(
            cmp_long,
            x=target_cat,
            y='Выручка с НДС',
            color='Период',
            barmode='group',
            title='Сравнение структуры выручки по категориям'
        )
        st.plotly_chart(ui.update_chart_layout(fig_cmp), use_container_width=True)
