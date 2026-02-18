import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logging
import ui
import telegram_utils
from io import BytesIO
from datetime import datetime, timedelta
import data_engine
from services import parsing_service
from services import analytics_service

logger = logging.getLogger(__name__)

# --- EXCEL EXPORT ---
@st.cache_data
def convert_df_to_excel(df, sort_mode, target_date_str):
    output = BytesIO()
    try:
        exp_df = df.copy()
        
        # Normalize
        if 'Фудкост' in exp_df.columns and 'Кост %' not in exp_df.columns:
            exp_df['Кост %'] = exp_df['Фудкост']
        if 'Кост %' not in exp_df.columns:
             exp_df['Кост %'] = (exp_df['Себестоимость'] / exp_df['Выручка с НДС'] * 100).fillna(0)
        
        # Sort
        if "Выручке" in sort_mode:
            exp_df = exp_df.sort_values(by='Выручка с НДС', ascending=False)
            sort_col = 'Выручка'
            source_metric_col = 'Выручка с НДС'
        elif "Фуд-косту" in sort_mode:
            exp_df = exp_df.sort_values(by='Кост %', ascending=False)
            sort_col = 'Кост %'
            source_metric_col = 'Кост %'
        elif "Количеству" in sort_mode:
            exp_df = exp_df.sort_values(by='Количество', ascending=False)
            sort_col = 'Кол-во'
            source_metric_col = 'Количество'
        else:
            sort_col = 'Выручка'
            source_metric_col = 'Выручка с НДС'
        
        # Map
        cols_map = {
            'Блюдо': 'Наименование', 
            'Количество': 'Кол-во', 
            'Себестоимость': 'Себест.', 
            'Выручка с НДС': 'Выручка', 
            'Кост %': 'Кост %', 
            'Категория': 'Категория',
            'Макро_Категория': 'Макро_Категория'
        }
        available_cols = [c for c in cols_map.keys() if c in exp_df.columns]
        final_df = exp_df[available_cols].rename(columns=cols_map)
        if 'Кост %' in final_df.columns:
            final_df['Кост %'] = final_df['Кост %'] / 100.0
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Report')
            workbook  = writer.book
            worksheet = writer.sheets['Report']
            
            # Formats
            fmt_header = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            fmt_money = workbook.add_format({'num_format': '#,##0 ₽'})
            fmt_pct = workbook.add_format({'num_format': '0.0%'}) 
            fmt_int = workbook.add_format({'num_format': '0'})

            for col_num, value in enumerate(final_df.columns.values):
                worksheet.write(0, col_num, value, fmt_header)
                
            for i, col in enumerate(final_df.columns):
                width = 15
                fmt = None
                if col in ['Выручка', 'Себест.']:
                    width = 18; fmt = fmt_money
                elif col == 'Кост %':
                    width = 12; fmt = fmt_pct
                elif col == 'Кол-во':
                    width = 10; fmt = fmt_int
                elif col == 'Наименование':
                    width = 40
                worksheet.set_column(i, i, width, fmt)

            # Charts Sheet
            charts_sheet = workbook.add_worksheet('Charts')
            
            # 1. Top 10 Column
            chart_col = workbook.add_chart({'type': 'column'})
            max_row = min(10, len(final_df))
            try:
                val_idx = final_df.columns.get_loc(sort_col)
                chart_col.add_series({
                    'name':       ['Report', 0, val_idx],
                    'categories': ['Report', 1, 0, max_row, 0],
                    'values':     ['Report', 1, val_idx, max_row, val_idx],
                    'data_labels': {'value': True},
                })
                chart_col.set_title({'name': f'Топ-10: {sort_col}'})
                charts_sheet.insert_chart('B2', chart_col, {'x_scale': 2.5, 'y_scale': 2})
            except Exception as exc:
                logger.warning("Failed to build Top-10 chart: %s", exc)

            # 2. Pie (Micro)
            if 'Категория' in final_df.columns:
                try:
                    cat_df = final_df.groupby('Категория')[sort_col].sum().reset_index().sort_values(by=sort_col, ascending=False)
                    charts_sheet.write(0, 14, 'Категория', fmt_header)
                    charts_sheet.write(0, 15, sort_col, fmt_header)
                    for r_idx, row in cat_df.iterrows():
                        charts_sheet.write(r_idx + 1, 14, row['Категория'])
                        charts_sheet.write(r_idx + 1, 15, row[sort_col], fmt_money)
                    
                    chart_pie = workbook.add_chart({'type': 'pie'})
                    chart_pie.add_series({
                        'name': 'Доли',
                        'categories': ['Charts', 1, 14, len(cat_df), 14],
                        'values': ['Charts', 1, 15, len(cat_df), 15],
                        'data_labels': {'percentage': True},
                    })
                    chart_pie.set_title({'name': f'Доли: {sort_col}'})
                    charts_sheet.insert_chart('J2', chart_pie, {'x_scale': 1.5, 'y_scale': 1.5})
                except Exception as exc:
                    logger.warning("Failed to build category pie chart: %s", exc)

            # 3. Donut (Macro)
            if 'Макро_Категория' in exp_df.columns:
                try:
                    macro_df = (
                        exp_df.groupby('Макро_Категория')[source_metric_col]
                        .sum()
                        .reset_index()
                        .sort_values(by=source_metric_col, ascending=False)
                    )
                    charts_sheet.write(0, 17, 'Макро', fmt_header)
                    charts_sheet.write(0, 18, sort_col, fmt_header)
                    for r_idx, row in macro_df.iterrows():
                        charts_sheet.write(r_idx + 1, 17, row['Макро_Категория'])
                        charts_sheet.write(r_idx + 1, 18, row[source_metric_col], fmt_money)
                        
                    chart_donut = workbook.add_chart({'type': 'doughnut'})
                    chart_donut.add_series({
                        'name': 'Структура (Макро)',
                        'categories': ['Charts', 1, 17, len(macro_df), 17],
                        'values': ['Charts', 1, 18, len(macro_df), 18],
                        'data_labels': {'percentage': True},
                    })
                    chart_donut.set_title({'name': 'Структура (Макро)'})
                    chart_donut.set_rotation(90)
                    charts_sheet.insert_chart('B18', chart_donut, {'x_scale': 1.5, 'y_scale': 1.5})
                except Exception as exc:
                    logger.warning("Failed to build macro donut chart: %s", exc)
                
    except Exception as e:
        logger.exception("Excel export failed: %s", e)
        return None
    return output.getvalue()


# --- RENDERERS ---

def render_kpi(df_current, df_prev, period_title):
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
    
    st.write(f"### 📊 Сводка: {period_title}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Выручка", f"{cur_rev:,.0f} ₽", f"{cur_rev - prev_rev:+,.0f} ₽" if not df_prev.empty else None)
    c2.metric("📉 Фуд-кост", f"{cur_fc:.1f} %", f"{cur_fc - prev_fc:+.1f} %" if not df_prev.empty else None, delta_color="inverse")
    c3.metric("💳 Маржа", f"{cur_margin:,.0f} ₽", f"{cur_margin - prev_margin:+,.0f} ₽" if not df_prev.empty else None)
    c4.metric("🧾 Позиций", len(df_current))

def render_sidebar_export(df_current, df_full, tg_token, tg_chat, target_date):
    with st.sidebar.expander("⚡ Действия и Экспорт", expanded=False):
        if st.button("📤 Отчет в Telegram", use_container_width=True):
            if not tg_token or not tg_chat:
                st.error("❌ Нет токена/чата!")
            elif df_current.empty:
                st.warning("⚠️ Нет данных.")
            else:
                with st.spinner("Формирую отчет..."):
                    try:
                        report_text = telegram_utils.format_report(df_full, target_date)
                        success, msg = telegram_utils.send_to_all(tg_token, tg_chat, report_text)
                        if success: st.success("Отправлено!")
                        else: st.error(msg)
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
        
        st.divider()
        
        if not df_current.empty:
            sort_opt = st.radio(
                "Сортировка Excel:",
                ["💰 По Выручке", "📉 По Фуд-косту", "📦 По Количеству"],
                index=0
            )
            excel_data = convert_df_to_excel(df_current, sort_opt, str(target_date.date()))
            
            if excel_data:
                st.download_button(
                    label="📊 Скачать Excel (+Графики)",
                    data=excel_data,
                    file_name=f"report_{target_date.strftime('%d-%m-%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.error("Ошибка генерации Excel")

def render_inflation(df_full, df_current, target_date, inflation_start_date=None):
    target_dt = pd.to_datetime(target_date)
    if inflation_start_date is not None:
        start_dt = pd.to_datetime(inflation_start_date)
        scope = df_full[(df_full['Дата_Отчета'] >= start_dt) & (df_full['Дата_Отчета'] <= target_dt)]
        if scope.empty or df_current.empty:
            loss, save, det = 0, 0, pd.DataFrame()
        else:
            old_prices = scope.sort_values('Дата_Отчета').groupby('Блюдо')['Unit_Cost'].first()
            current_prices = df_current.groupby('Блюдо')['Unit_Cost'].mean()
            merged = pd.concat([old_prices, current_prices], axis=1, keys=['Old', 'New']).dropna()
            merged['Diff'] = merged['New'] - merged['Old']
            merged['Pct'] = (merged['Diff'] / merged['Old']) * 100
            merged = merged.replace([float('inf'), float('-inf')], pd.NA).dropna(subset=['Pct'])
            qty_map = df_current.groupby('Блюдо')['Количество'].sum()
            merged['Qty'] = qty_map
            merged['Effect'] = merged['Diff'] * merged['Qty']
            loss = merged[merged['Effect'] > 0]['Effect'].sum()
            save = abs(merged[merged['Effect'] < 0]['Effect'].sum())
            det = merged[merged['Effect'] != 0].copy()
            det['Товар'] = det.index
            det['Рост %'] = det['Pct']
            det['Эффект (₽)'] = det['Effect']
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
            st.dataframe(det[det['Эффект (₽)'] > 0].sort_values('Эффект (₽)', ascending=False).head(20)[['Товар', 'Рост %', 'Эффект (₽)']], use_container_width=True)
        with c2:
            st.caption("Топ падения (Экономия)")
            st.dataframe(det[det['Эффект (₽)'] < 0].sort_values('Эффект (₽)', ascending=True).head(20)[['Товар', 'Рост %', 'Эффект (₽)']], use_container_width=True)

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
    view_mode = st.radio("Вид:", ["Макро", "Микро"], horizontal=True, label_visibility="collapsed")
    target_cat = 'Макро_Категория' if view_mode == "Макро" else 'Категория'
    
    cats, items = analytics_service.compute_menu_tab_data(df_current, target_cat)
    
    c1, c2 = st.columns([1, 1.5])
    with c1:
        # Clean donut: group small categories into "Прочее" and simplify legend
        cats_sorted = cats.sort_values('Выручка с НДС', ascending=False).copy()
        total_rev = cats_sorted['Выручка с НДС'].sum()
        if total_rev > 0:
            cats_sorted['share'] = cats_sorted['Выручка с НДС'] / total_rev
            small_mask = cats_sorted['share'] < 0.03
            if small_mask.any():
                other_sum = cats_sorted.loc[small_mask, 'Выручка с НДС'].sum()
                cats_sorted = cats_sorted.loc[~small_mask, [target_cat, 'Выручка с НДС']]
                cats_sorted = pd.concat(
                    [cats_sorted, pd.DataFrame({target_cat: ["📦 Прочее"], "Выручка с НДС": [other_sum]})],
                    ignore_index=True
                )
        fig = px.pie(
            cats_sorted,
            values='Выручка с НДС',
            names=target_cat,
            hole=0.55,
            title="Структура выручки"
        )
        fig.update_traces(textposition='inside', textinfo='percent', insidetextorientation='radial')
        fig.update_layout(
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            title=dict(x=0.5, y=0.97, xanchor="center", yanchor="top"),
            margin=dict(l=10, r=10, t=60, b=120)
        )
        st.plotly_chart(ui.update_chart_layout(fig), use_container_width=True)
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
            st.dataframe(
                df_fc,
                column_config={
                    "С/С начало периода": st.column_config.NumberColumn(format="%.2f ₽"),
                    "С/С конец периода": st.column_config.NumberColumn(format="%.2f ₽"),
                    "Факт фудкост %": st.column_config.NumberColumn(format="%.1f %%"),
                    "Выручка с НДС": st.column_config.NumberColumn(format="%.0f ₽"),
                    "Кол-во продано": st.column_config.NumberColumn(format="%.0f"),
                },
                use_container_width=True,
                height=400
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

def render_abc(df_current):
    abc, aq, am = analytics_service.compute_abc_data(df_current)
    if abc.empty:
        st.info("Нет данных")
        return
        
    st.info(f"Средние продажи: {aq:.1f} шт | Средняя маржа с шт: {am:.0f} ₽")
    fig = px.scatter(
        abc, x="Количество", y="Unit_Margin", color="Класс", size="Выручка с НДС", log_x=True,
        color_discrete_map={"⭐ Звезда": "blue", "🐎 Лошадка": "gold", "❓ Загадка": "green", "🐶 Собака": "red"},
        hover_name="Блюдо"
    )
    fig.add_vline(x=aq, line_dash="dash", line_color="gray")
    fig.add_hline(y=am, line_dash="dash", line_color="gray")
    st.plotly_chart(ui.update_chart_layout(fig), use_container_width=True)

    with st.expander("📋 Таблица ABC", expanded=False):
        with st.container():
            c_a1, c_a2 = st.columns(2)
            with c_a1:
                abc_min_rev = st.number_input("Мин. выручка (₽) ", min_value=0, value=0, step=1000, key="abc_min_rev")
                abc_min_qty = st.number_input("Мин. кол-во ", min_value=0, value=0, step=10, key="abc_min_qty")
            with c_a2:
                abc_top_n = st.slider("Показать топ N по выручке ", 10, 300, 150, key="abc_top_n")

        abc_view = abc.rename(columns={
            "Блюдо": "Блюдо",
            "Выручка с НДС": "Выручка",
            "Себестоимость": "С/С",
            "Количество": "Кол-во",
            "Unit_Margin": "Маржа/шт",
            "Класс": "Класс"
        })
        abc_view = abc_view[(abc_view["Выручка"] >= abc_min_rev) & (abc_view["Кол-во"] >= abc_min_qty)]
        abc_view = abc_view.sort_values("Выручка", ascending=False).head(abc_top_n)
        st.dataframe(
            abc_view[["Блюдо", "Класс", "Выручка", "С/С", "Кол-во", "Маржа/шт"]],
            column_config={
                "Выручка": st.column_config.NumberColumn(format="%.0f ₽"),
                "С/С": st.column_config.NumberColumn(format="%.0f ₽"),
                "Кол-во": st.column_config.NumberColumn(format="%.0f"),
                "Маржа/шт": st.column_config.NumberColumn(format="%.0f ₽"),
            },
            use_container_width=True,
            height=400
        )

def render_simulator(df_current, df_full):
    st.subheader("🔮 Симулятор: Анализ 'Что если?'")
    
    c_in, c_res = st.columns([1, 2])
    with c_in:
        all_cats = sorted(df_full['Категория'].dropna().unique())
        sel_cats = st.multiselect("Категории:", all_cats, default=all_cats[:3] if len(all_cats)>3 else all_cats)
        
        st.markdown("---")
        d_price = st.slider("Цена продажи (%)", -50, 50, 0)
        d_cost = st.slider("Себестоимость (%)", -50, 50, 0)
        d_vol = st.slider("Объем продаж (%)", -50, 50, 0)

    with c_res:
        if sel_cats:
            res = analytics_service.compute_simulation(df_current, sel_cats, d_price, d_cost, d_vol)
            if res:
                k1, k2, k3 = st.columns(3)
                k1.metric("Новая Выручка", f"{res['sim_revenue']:,.0f} ₽", f"{res['diff_rev']:+,.0f} ₽")
                k2.metric("Новая Маржа", f"{res['sim_margin']:,.0f} ₽", f"{res['diff_margin']:+,.0f} ₽")
                k3.metric("Рентабельность", f"{res['new_profitability']:.1f}%", f"{res['new_profitability'] - res['old_profitability']:+.1f}%")
                
                comp_df = pd.DataFrame([
                    {'Metric': 'Маржа', 'Scenario': 'Было', 'Value': res['base_margin']},
                    {'Metric': 'Маржа', 'Scenario': 'Стало', 'Value': res['sim_margin']}
                ])
                fig = px.bar(comp_df, x='Scenario', y='Value', color='Scenario', title="Сравнение Маржи")
                st.plotly_chart(ui.update_chart_layout(fig), use_container_width=True)

def render_weekdays(df_current, df_prev, current_label="", prev_label=""):
    daily_cur, weekday_cur = analytics_service.compute_weekday_stats(df_current)
    if weekday_cur.empty:
        st.info("Нет данных для анализа дней недели.")
        return

    c1, c2 = st.columns(2)
    with c1:
        if not df_prev.empty:
            _, weekday_prev = analytics_service.compute_weekday_stats(df_prev)
            cur_cmp = weekday_cur.rename(columns={'Выручка с НДС': 'Текущий'})
            prev_cmp = weekday_prev.rename(columns={'Выручка с НДС': 'Сравнение'})
            cmp_df = cur_cmp.merge(prev_cmp, on='ДеньРус', how='outer').fillna(0)
            cmp_long = cmp_df.melt(
                id_vars=['ДеньРус'],
                value_vars=['Текущий', 'Сравнение'],
                var_name='Период',
                value_name='Выручка с НДС'
            )
            period_names = {
                'Текущий': current_label or 'Текущий период',
                'Сравнение': prev_label or 'Период сравнения',
            }
            cmp_long['Период'] = cmp_long['Период'].map(period_names)
            fig_avg = px.bar(
                cmp_long,
                x='ДеньРус',
                y='Выручка с НДС',
                color='Период',
                barmode='group',
                title='Средняя выручка по дням недели'
            )
        else:
            fig_avg = px.bar(weekday_cur, x='ДеньРус', y='Выручка с НДС', title='Средняя выручка по дням недели')
        st.plotly_chart(ui.update_chart_layout(fig_avg), use_container_width=True)

    with c2:
        daily_cur = daily_cur.sort_values('Дата_Отчета').copy()
        daily_cur['ИндексДня'] = range(1, len(daily_cur) + 1)
        fig_daily = go.Figure()
        fig_daily.add_trace(go.Scatter(
            x=daily_cur['ИндексДня'],
            y=daily_cur['Выручка с НДС'],
            mode='lines+markers',
            name=current_label or 'Текущий период',
            text=daily_cur['ДеньРус'],
            customdata=daily_cur['Дата_Подпись'],
            hovertemplate='День #%{x}<br>%{customdata} (%{text})<br>Выручка: %{y:,.0f} ₽<extra></extra>'
        ))

        if not df_prev.empty:
            daily_prev, _ = analytics_service.compute_weekday_stats(df_prev)
            daily_prev = daily_prev.sort_values('Дата_Отчета').copy()
            daily_prev['ИндексДня'] = range(1, len(daily_prev) + 1)
            fig_daily.add_trace(go.Scatter(
                x=daily_prev['ИндексДня'],
                y=daily_prev['Выручка с НДС'],
                mode='lines+markers',
                name=prev_label or 'Период сравнения',
                text=daily_prev['ДеньРус'],
                customdata=daily_prev['Дата_Подпись'],
                hovertemplate='День #%{x}<br>%{customdata} (%{text})<br>Выручка: %{y:,.0f} ₽<extra></extra>'
            ))

        fig_daily.update_layout(title='Дневная динамика внутри периода', xaxis_title='Номер дня периода')
        st.plotly_chart(ui.update_chart_layout(fig_daily), use_container_width=True)

def render_procurement_v2(df_sales, df_full, period_days):
    st.subheader("📦 Планирование Закупок")
    
    recipes_map = data_engine.get_recipes_map()
    stock_df = data_engine.get_stock_data()
    
    if not recipes_map:
        st.warning("⚠️ Не найдены технологические карты (TTK). Загрузите их в папку 'TechnologicalMaps'.")
        return
        
    if stock_df is None or stock_df.empty:
        st.warning("⚠️ Не найдены остатки (Оборотка). Загрузите файлы в папку 'ProductTurnover'.")
        return

    # --- UI CONTROLS ---
    c_method, c_days = st.columns([2, 1])
    with c_method:
        forecast_method = st.radio(
            "Метод прогноза:",
            ["📊 Среднее по выбранному периоду", "🧠 Умный прогноз (Тренд + Прошлый год)"],
            horizontal=True
        )
    with c_days:
         target_days = st.slider("На сколько дней закупаем?", 1, 30, 7)

    preset_mode = st.selectbox(
        "Режим прогноза",
        ["Авто (рекомендуется)", "Стабильно", "Агрессивно", "Пользовательский"],
        index=0
    )

    # Defaults for presets
    preset_params = {
        "Авто (рекомендуется)": dict(
            lead_time=3, trend_window_days=28, ly_window_days=14, sigma_window_days=56,
            service_level=95, holiday_boost=20, trend_weight=0.6, ly_weight=0.4,
            use_weekday_yoy=True, yoy_cap=1.5
        ),
        "Стабильно": dict(
            lead_time=3, trend_window_days=42, ly_window_days=21, sigma_window_days=90,
            service_level=98, holiday_boost=10, trend_weight=0.4, ly_weight=0.6,
            use_weekday_yoy=True, yoy_cap=1.3
        ),
        "Агрессивно": dict(
            lead_time=2, trend_window_days=21, ly_window_days=10, sigma_window_days=42,
            service_level=90, holiday_boost=30, trend_weight=0.75, ly_weight=0.25,
            use_weekday_yoy=True, yoy_cap=1.8
        ),
    }

    with st.expander("⚙️ Параметры прогноза (расширенные)", expanded=(preset_mode == "Пользовательский")):
        c1, c2, c3 = st.columns(3)
        with c1:
            lead_time = st.slider("Lead time (дней)", 0, 21, 3)
            trend_window_days = st.slider("Окно тренда (дней)", 14, 120, 28)
        with c2:
            service_level = st.selectbox("Service level", [80, 90, 95, 98], index=2)
            holiday_boost = st.slider("Коэф. праздников (%)", 0, 100, 20)
            ly_window_days = st.slider("Окно прошлого года (±дней)", 7, 45, 14)
        with c3:
            trend_weight = st.slider("Вес тренда", 0.0, 1.0, 0.6)
            ly_weight = st.slider("Вес прошлого года", 0.0, 1.0, 0.4)
            sigma_window_days = st.slider("Окно волатильности (дней)", 14, 180, 56)
            pack_size_default = st.number_input("Кратность (упаковка)", 0.0, 10000.0, 0.0)
            min_order_default = st.number_input("Мин. заказ (MOQ)", 0.0, 10000.0, 0.0)
            use_weekday_yoy = st.checkbox("Усилить сравнение по дням недели (YoY)", value=True)
            yoy_cap = st.slider("Ограничение YoY коэффициента", 0.5, 2.0, 1.5)

        st.caption("Праздники: введите даты в формате `YYYY-MM-DD` или `DD.MM.YYYY`, по одной в строке.")
        holiday_text = st.text_area("Доп. праздники", value="", height=100)

    if preset_mode != "Пользовательский":
        p = preset_params[preset_mode]
        lead_time = p["lead_time"]
        trend_window_days = p["trend_window_days"]
        ly_window_days = p["ly_window_days"]
        sigma_window_days = p["sigma_window_days"]
        service_level = p["service_level"]
        holiday_boost = p["holiday_boost"]
        trend_weight = p["trend_weight"]
        ly_weight = p["ly_weight"]
        use_weekday_yoy = p["use_weekday_yoy"]
        yoy_cap = p["yoy_cap"]
        st.info(f"Режим: {preset_mode}. Используются встроенные параметры.")

    days_in_period = max(1, period_days)

    # --- HELPER: Get Consumption DataFrame ---
    def get_consumption(df_source, days_count):
        if df_source.empty: return pd.DataFrame(columns=["ingredient", "unit", "qty_needed"])
        
        # Group sales
        s_grouped = df_source.groupby("Блюдо")["Количество"].sum().reset_index()
        s_grouped["norm_dish"] = s_grouped["Блюдо"].apply(lambda x: parsing_service.normalize_name(str(x)))
        
        cons_data = []
        for _, row in s_grouped.iterrows():
            name = row["norm_dish"]
            qty = row["Количество"]
            ingredients = recipes_map.get(name)
            if ingredients:
                for ing in ingredients:
                    cons_data.append({
                        "ingredient": ing["ingredient"],
                        "unit": ing["unit"],
                        "qty_needed": ing["qty_per_dish"] * qty
                    })
        
        if not cons_data: return pd.DataFrame(columns=["ingredient", "unit", "qty_needed"])
        
        df_c = pd.DataFrame(cons_data)
        return df_c.groupby(["ingredient", "unit"])["qty_needed"].sum().reset_index()

    # --- 1. CURRENT PERIOD CONSUMPTION ---
    # This is always calculated to show "Current Usage"
    df_cons_current = get_consumption(df_sales, days_in_period)
    df_cons_current["avg_current"] = df_cons_current["qty_needed"] / days_in_period

    # --- 2. SMART FORECAST (WEEKDAY AWARE) ---
    df_forecast = pd.DataFrame()
    sigma_map = {}
    
    if "Умный" in forecast_method:
        # 2. Helper to get Weekday Profiles (Sales Based) with RECURSION
        # SWITCH: Use History or Sales?
        df_history = data_engine.get_turnover_history()
        use_history = df_history is not None and not df_history.empty

        profile_trend = {}
        profile_ly = {}

        # Ensure datetime in history
        if use_history and not pd.api.types.is_datetime64_any_dtype(df_history['date']):
            df_history['date'] = pd.to_datetime(df_history['date'])

        # 1. Determine Target Dates (Tomorrow -> Tomorrow + N)
        # Since reports might be old, we use: LastReportDate + 1 -> + N
        if use_history:
            last_report_date = df_history['date'].max()
        else:
            last_report_date = df_full['Дата_Отчета'].max()
        target_dates = [last_report_date + timedelta(days=i) for i in range(1, target_days + 1)]
        target_weekdays = [d.weekday() for d in target_dates] # 0=Mon, 6=Sun

        # Holidays (base + manual)
        # РФ 2026 (производственный календарь): периоды отдыха с переносами
        # Источник: КонсультантПлюс (праздники и перенос выходных в 2026 г.)
        def get_ru_holidays(year):
            holidays = set()
            if year == 2025:
                # 29.12.2024–08.01.2025
                holidays.update(pd.date_range("2024-12-29", "2025-01-08").date)
                # 22–23.02.2025
                holidays.update(pd.date_range("2025-02-22", "2025-02-23").date)
                # 08–09.03.2025
                holidays.update(pd.date_range("2025-03-08", "2025-03-09").date)
                # 01–04.05.2025
                holidays.update(pd.date_range("2025-05-01", "2025-05-04").date)
                # 08–11.05.2025
                holidays.update(pd.date_range("2025-05-08", "2025-05-11").date)
                # 12–15.06.2025
                holidays.update(pd.date_range("2025-06-12", "2025-06-15").date)
                # 02–04.11.2025
                holidays.update(pd.date_range("2025-11-02", "2025-11-04").date)
                # 31.12.2025
                holidays.add(pd.to_datetime("2025-12-31").date())
            if year == 2026:
                # 31.12.2025–11.01.2026
                holidays.update(pd.date_range("2025-12-31", "2026-01-11").date)
                # 21–23.02.2026
                holidays.update(pd.date_range("2026-02-21", "2026-02-23").date)
                # 07–09.03.2026
                holidays.update(pd.date_range("2026-03-07", "2026-03-09").date)
                # 01–03.05.2026
                holidays.update(pd.date_range("2026-05-01", "2026-05-03").date)
                # 09–11.05.2026
                holidays.update(pd.date_range("2026-05-09", "2026-05-11").date)
                # 12–14.06.2026
                holidays.update(pd.date_range("2026-06-12", "2026-06-14").date)
                # 04.11.2026
                holidays.add(pd.to_datetime("2026-11-04").date())
                # 31.12.2026
                holidays.add(pd.to_datetime("2026-12-31").date())
            return holidays

        base_holidays = {
            "01-01", "01-02", "01-03", "01-04", "01-05", "01-06", "01-07", "01-08",
            "02-23", "03-08", "05-01", "05-09", "06-12", "11-04"
        }
        manual_holidays = set()
        for line in holiday_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                manual_holidays.add(pd.to_datetime(line, dayfirst=True).date())
            except Exception:
                pass

        holiday_dates = set(manual_holidays)
        for d in target_dates:
            if d.strftime("%m-%d") in base_holidays:
                holiday_dates.add(d.date())

        years_in_targets = {d.year for d in target_dates}
        for y in years_in_targets:
            holiday_dates.update(get_ru_holidays(y))

        def explode_sales_to_ingredients(df_src):
            if df_src.empty:
                return pd.DataFrame(columns=["date", "ingredient", "qty"])
            df_src = df_src.copy()
            daily_sales = df_src.groupby(['Дата_Отчета', 'Блюдо'])['Количество'].sum().reset_index()
            daily_sales['norm_dish'] = daily_sales['Блюдо'].apply(lambda x: parsing_service.normalize_name(str(x)))
            rows = []

            def resolve_ingredients(name, qty_needed, dt, depth=0):
                if depth > 10:
                    return
                ings = recipes_map.get(name)
                if ings:
                    for ing in ings:
                        i_name = ing['ingredient']
                        sub_qty = qty_needed * ing['qty_per_dish']
                        resolve_ingredients(i_name, sub_qty, dt, depth + 1)
                else:
                    rows.append({"date": dt, "ingredient": name, "qty": qty_needed})

            for _, row in daily_sales.iterrows():
                resolve_ingredients(row["norm_dish"], row["Количество"], row["Дата_Отчета"])
            if not rows:
                return pd.DataFrame(columns=["date", "ingredient", "qty"])
            return pd.DataFrame(rows)

        def get_combined_daily(start_date, end_date):
            # Sales-based daily ingredients
            df_sales_range = df_full[(df_full['Дата_Отчета'] >= start_date) & (df_full['Дата_Отчета'] <= end_date)]
            df_sales_ing = explode_sales_to_ingredients(df_sales_range)
            if not df_sales_ing.empty:
                df_sales_ing = df_sales_ing.groupby(['ingredient', 'date'])['qty'].sum().reset_index()

            # History-based daily ingredients
            df_hist_ing = pd.DataFrame(columns=["ingredient", "date", "qty_out"])
            if use_history:
                df_hist_ing = df_history[(df_history['date'] >= start_date) & (df_history['date'] <= end_date)].copy()
                if not df_hist_ing.empty:
                    # Exclude semi-finished (have recipes)
                    df_hist_ing = df_hist_ing[~df_hist_ing['ingredient'].isin(recipes_map.keys())]
                    df_hist_ing = df_hist_ing.groupby(['ingredient', 'date'])['qty_out'].sum().reset_index()

            if df_hist_ing.empty and df_sales_ing.empty:
                return pd.DataFrame(columns=["ingredient", "date", "qty"])

            df_combined = pd.merge(
                df_sales_ing.rename(columns={"qty": "qty_sales"}),
                df_hist_ing.rename(columns={"qty_out": "qty_hist"}),
                on=["ingredient", "date"],
                how="outer"
            )
            df_combined["qty"] = df_combined["qty_hist"].where(df_combined["qty_hist"].notna(), df_combined["qty_sales"])
            return df_combined[["ingredient", "date", "qty"]].fillna(0)

        def get_weekday_profile_from_daily(df_daily):
            if df_daily.empty:
                return {}
            df_daily = df_daily.copy()
            df_daily['weekday'] = df_daily['date'].dt.weekday
            grp = df_daily.groupby(['ingredient', 'weekday'])['qty'].median()
            profile = {}
            for (ing, wd), qty in grp.items():
                if ing not in profile:
                    profile[ing] = {w: 0.0 for w in range(7)}
                profile[ing][wd] = qty
            return profile

        # Trend window
        trend_start = last_report_date - timedelta(days=trend_window_days)
        df_trend_daily = get_combined_daily(trend_start, last_report_date)
        profile_trend = get_weekday_profile_from_daily(df_trend_daily)

        # Seasonal (Last Year window)
        ly_center = last_report_date - timedelta(days=365)
        ly_start = ly_center - timedelta(days=ly_window_days)
        ly_end = ly_center + timedelta(days=ly_window_days)
        df_ly_daily = get_combined_daily(ly_start, ly_end)
        profile_ly = get_weekday_profile_from_daily(df_ly_daily)

        # 3b. Daily consumption stats for safety stock
        avg_current_map = dict(zip(df_cons_current["ingredient"], df_cons_current["avg_current"])) if not df_cons_current.empty else {}
        if not df_sales.empty and use_history:
            period_start = df_sales['Дата_Отчета'].min()
            period_end = df_sales['Дата_Отчета'].max()
            df_period_daily = get_combined_daily(period_start, period_end)
            if not df_period_daily.empty:
                avg_current_map = (df_period_daily.groupby('ingredient')['qty'].sum() / days_in_period).to_dict()

        def compute_sigma_map():
            end_date = last_report_date
            start_date = last_report_date - timedelta(days=sigma_window_days - 1)
            date_index = pd.date_range(start_date, end_date, freq="D")
            sigma_map = {}

            df_sigma = get_combined_daily(start_date, end_date)
            if df_sigma.empty:
                return sigma_map
            df_sigma['date'] = pd.to_datetime(df_sigma['date'])
            agg = df_sigma.groupby(['ingredient', 'date'])['qty'].sum().reset_index()
            for ing, sub in agg.groupby('ingredient'):
                series = pd.Series(0.0, index=date_index)
                sub_series = sub.set_index('date')['qty']
                series.loc[sub_series.index] = sub_series.values
                sigma_map[ing] = float(series.std(ddof=0))
            return sigma_map

        sigma_map = compute_sigma_map()
        
        # 4. Calculate Demand for Target Dates
        final_forecast = []

        # Normalize weights
        wt = max(0.0, trend_weight)
        wl = max(0.0, ly_weight)
        if wt + wl == 0:
            wt, wl = 0.5, 0.5
        else:
            wt, wl = wt / (wt + wl), wl / (wt + wl)
        
        # Get all ingredients
        all_ings = set(profile_trend.keys()) | set(profile_ly.keys())
        
        for ing in all_ings:
            p_trend = profile_trend.get(ing, {w: 0.0 for w in range(7)})
            p_ly = profile_ly.get(ing, {w: 0.0 for w in range(7)})
            avg_current = avg_current_map.get(ing, 0.0)
            
            total_need = 0.0
            sum_trend = 0.0
            sum_ly = 0.0
            sum_holiday_factor = 0.0
            
            for dt, wd in zip(target_dates, target_weekdays):
                # Forecast for this specific day = (Trend[wd] + LY[wd]) / 2
                val_t = p_trend[wd]
                val_l = p_ly[wd]

                # Weekday YoY adjustment: compare this year's recent weekday vs last year's weekday
                if use_weekday_yoy and val_l > 0:
                    ratio = val_t / val_l
                    if ratio < 1.0 / yoy_cap:
                        ratio = 1.0 / yoy_cap
                    elif ratio > yoy_cap:
                        ratio = yoy_cap
                    val_l = val_l * ratio
                
                sum_trend += val_t
                sum_ly += val_l
                
                day_val = (val_t * wt) + (val_l * wl)
                if day_val == 0.0 and avg_current > 0:
                    day_val = avg_current

                holiday_factor = 1.0
                if dt.date() in holiday_dates:
                    holiday_factor = (1 + holiday_boost / 100.0)
                    day_val = day_val * holiday_factor
                sum_holiday_factor += holiday_factor
                
                total_need += day_val
                
            # Avg metrics for display
            avg_daily_trend = sum_trend / target_days
            avg_daily_ly = sum_ly / target_days
            daily_forecast = total_need / target_days
            avg_holiday_factor = sum_holiday_factor / target_days if target_days > 0 else 1.0
            
            final_forecast.append({
                "ingredient": ing,
                "daily_forecast": daily_forecast, # This is technically "Avg Need for Target Period"
                "avg_trend": avg_daily_trend,
                "avg_ly": avg_daily_ly,
                "holiday_factor": avg_holiday_factor,
                "wt": wt,
                "wl": wl,
            })
            
        df_forecast = pd.DataFrame(final_forecast)
        if df_forecast.empty:
            df_forecast = pd.DataFrame(columns=["ingredient", "daily_forecast", "avg_trend", "avg_ly"])

    else:
        # Simple Mode: Forecast = Current Period Avg
        df_forecast = df_cons_current[["ingredient", "avg_current"]].rename(columns={"avg_current": "daily_forecast"})
        df_forecast["avg_trend"] = 0.0
        df_forecast["avg_ly"] = 0.0

    # 3. Merge with Stock
    # We use df_forecast as the base for "Needs", but we also want to show current period usage for reference?
    # Actually, the procurement should be based on the Forecast.
    
    # Let's merge Forecast with Stock
    df_final = pd.merge(df_forecast, stock_df, on="ingredient", how="outer")
    
    # Fill NaNs
    df_final["daily_forecast"] = df_final["daily_forecast"].fillna(0)
    df_final["stock_qty"] = df_final["stock_qty"].fillna(0)
    df_final["avg_trend"] = df_final.get("avg_trend", pd.Series(0)).fillna(0)
    df_final["avg_ly"] = df_final.get("avg_ly", pd.Series(0)).fillna(0)
    df_final["holiday_factor"] = df_final.get("holiday_factor", pd.Series(1.0)).fillna(1.0)
    df_final["wt"] = df_final.get("wt", pd.Series(0.0)).fillna(0.0)
    df_final["wl"] = df_final.get("wl", pd.Series(0.0)).fillna(0.0)
    
    # Recover Unit (it might be lost in merges if not careful)
    # We can get unit from recipes or stock or consumption df
    # Let's try to fetch it from df_cons_current or stock
    
    # Helper to map units
    # Create valid unit map from all sources
    all_units = {}
    if not df_cons_current.empty: 
        all_units.update(dict(zip(df_cons_current.ingredient, df_cons_current.unit)))
    
    if "unit" in stock_df.columns:
        all_units.update(dict(zip(stock_df.ingredient, stock_df.unit))) 
    
    df_final["unit"] = df_final["ingredient"].map(all_units).fillna("")

    # 4. Analyze

    # Safety stock (simple, based on variability)
    z_map = {80: 0.84, 90: 1.28, 95: 1.65, 98: 2.05}
    z = z_map.get(service_level, 1.65)
    review_period = max(1, target_days)
    horizon = lead_time + review_period
    df_final["sigma_daily"] = df_final["ingredient"].map(sigma_map).fillna(df_final["daily_forecast"] * 0.25)
    df_final["safety_stock"] = z * df_final["sigma_daily"] * (horizon ** 0.5)
    on_order_cols = [c for c in ["on_order_qty", "in_transit", "in_transit_qty", "on_order"] if c in df_final.columns]
    if on_order_cols:
        df_final["on_order"] = df_final[on_order_cols[0]].fillna(0)
    else:
        df_final["on_order"] = 0.0
    
    # Days Left = Stock / Daily Forecast
    df_final["days_left"] = df_final.apply(
        lambda x: x["stock_qty"] / x["daily_forecast"] if x["daily_forecast"] > 0.001 else 999, 
        axis=1
    )
    
    df_final["to_buy"] = (df_final["daily_forecast"] * horizon) + df_final["safety_stock"] - df_final["stock_qty"] - df_final["on_order"]
    df_final["to_buy"] = df_final["to_buy"].apply(lambda x: max(0.0, x))

    # Apply MOQ / pack size if provided (use per-item overrides when available)
    pack_col = "pack_size" if "pack_size" in df_final.columns else None
    moq_col = "min_order_qty" if "min_order_qty" in df_final.columns else None

    def apply_pack_moq(row):
        qty = row["to_buy"]
        if qty <= 0:
            return 0.0
        pack = row[pack_col] if pack_col else pack_size_default
        moq = row[moq_col] if moq_col else min_order_default
        try:
            pack = float(pack) if pack is not None else 0.0
        except Exception:
            pack = 0.0
        try:
            moq = float(moq) if moq is not None else 0.0
        except Exception:
            moq = 0.0
        if pack and pack > 0:
            qty = (int((qty + pack - 1) // pack) * pack)
        if moq and moq > 0:
            qty = max(qty, moq)
        return qty

    df_final["to_buy"] = df_final.apply(apply_pack_moq, axis=1)
    
    # Filter: Show only relevant items
    df_view = df_final[(df_final["daily_forecast"] > 0) | (df_final["stock_qty"] > 0)].copy()
    
    # Sort
    df_view = df_view.sort_values("days_left", ascending=True)
    
    # Metrics Header
    st.info(f"📊 Загружено рецептов: {len(recipes_map)}. Позиций на складе: {len(stock_df)}")

    # Rename & Columns
    cols_to_show = ["ingredient", "unit", "stock_qty", "days_left", "to_buy", "safety_stock"]
    rename_map = {
        "ingredient": "Ингредиент",
        "unit": "Ед.",
        "stock_qty": "Остаток",
        "days_left": "Хватит (дней)",
        "to_buy": "Закупить",
        "safety_stock": "Страх. запас"
    }

    if "Умный" in forecast_method:
        trend_label = f"Тренд ({trend_window_days}д)"
        cols_to_show = cols_to_show[:2] + ["avg_trend", "avg_ly", "daily_forecast"] + cols_to_show[2:]
        rename_map.update({
            "avg_trend": trend_label,
            "avg_ly": "Прошлый год",
            "daily_forecast": "Прогноз/день",
            "holiday_factor": "Праздн. коэф."
        })
        cols_to_show = cols_to_show[:5] + ["holiday_factor"] + cols_to_show[5:]
    else:
        cols_to_show.insert(2, "daily_forecast")
        rename_map["daily_forecast"] = "Ср. расход/день"
        
    df_display = df_view[cols_to_show].rename(columns=rename_map)
    
    # Formatting
    format_dict = {
        "Остаток": "{:.2f}",
        "Хватит (дней)": "{:.0f}",
        "Закупить": "{:.2f}",
        "Ср. расход/день": "{:.2f}",
        "Прогноз/день": "{:.2f}",
        "Прошлый год": "{:.2f}",
        "Праздн. коэф.": "{:.2f}"
    }
    if "Умный" in forecast_method:
        format_dict[trend_label] = "{:.2f}"

    st.dataframe(
        df_display.style.format(format_dict).apply(
            lambda x: ["color: #e53935; font-weight: 700" if v < 3 else ("color: #f9a825; font-weight: 700" if v < 7 else "") for v in x],
            subset=["Хватит (дней)"]
        )
    )
