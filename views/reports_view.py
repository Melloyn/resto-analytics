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

logger = logging.getLogger(__name__)

# --- COMPUTATION HELPERS (Moved from app.py) ---
def compute_inflation_metrics(df_scope, df_v):
    if df_scope.empty or df_v.empty: return 0, 0, pd.DataFrame()
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

def compute_supplier_stats(df):
    if 'Поставщик' not in df.columns or df.empty: return pd.DataFrame()
    return df.groupby('Поставщик')['Себестоимость'].sum().reset_index().sort_values('Себестоимость', ascending=False).head(15)

def compute_menu_tab_data(df, group_col):
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    cat_df = df.groupby(group_col)['Выручка с НДС'].sum().reset_index().sort_values(by='Выручка с НДС', ascending=False)
    
    menu_df = df.groupby('Блюдо').agg({
        'Выручка с НДС': 'sum',
        'Себестоимость': 'sum',
        'Количество': 'sum'
    }).reset_index()
    menu_df['Фудкост %'] = (menu_df['Себестоимость'] / menu_df['Выручка с НДС'] * 100).fillna(0)
    menu_df = menu_df.sort_values('Выручка с НДС', ascending=False)
    return cat_df, menu_df

def compute_abc_data(df):
    if df.empty: return pd.DataFrame(), 0, 0
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
        if high_vol and high_prof: return "⭐ Звезда"
        if high_vol and not high_prof: return "🐎 Лошадка"
        if not high_vol and high_prof: return "❓ Загадка"
        return "🐶 Собака"

    abc['Класс'] = abc.apply(classify, axis=1)
    return abc, avg_qty, avg_margin

def compute_weekday_stats(df):
    if df.empty: return pd.DataFrame(), pd.DataFrame()

    ru_days = {
        0: 'Понедельник', 1: 'Вторник', 2: 'Среда', 3: 'Четверг',
        4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
    }

    # Daily dynamic
    daily = df.groupby('Дата_Отчета')['Выручка с НДС'].sum().reset_index()
    daily['ДеньРус'] = daily['Дата_Отчета'].dt.weekday.map(ru_days)
    daily['Дата_Подпись'] = daily['Дата_Отчета'].dt.strftime('%d.%m')
    
    # Weekday average
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

def compute_purchase_plan(df, days, safety):
    if df.empty: return pd.DataFrame(columns=['Budget'])
    end_dt = df['Дата_Отчета'].max()
    start_dt = end_dt - timedelta(days=30)
    recent = df[df['Дата_Отчета'] >= start_dt]
    
    daily_usage = recent.groupby('Блюдо')['Количество'].sum() / 30
    last_cost = recent.sort_values('Дата_Отчета').groupby('Блюдо')['Unit_Cost'].last()
    
    plan = pd.DataFrame({'Daily_Use': daily_usage, 'Unit_Cost': last_cost}).dropna()
    plan['Need_Qty'] = plan['Daily_Use'] * days * (1 + safety/100)
    plan['Budget'] = plan['Need_Qty'] * plan['Unit_Cost']
    
    return plan.sort_values('Budget', ascending=False).reset_index()

def compute_simulation(df, cats, d_price, d_cost, d_vol):
    if df.empty: return None
    mask = df['Категория'].isin(cats)
    target = df[mask].copy()
    other = df[~mask].copy()
    
    # Base
    base_rev = df['Выручка с НДС'].sum()
    base_cost = df['Себестоимость'].sum()
    base_margin = base_rev - base_cost
    
    # Sim
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

def render_inflation(df_full, df_current, target_date):
    loss, save, det = compute_inflation_metrics(df_full[df_full['Дата_Отчета'] <= pd.to_datetime(target_date)], df_current)
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
        stats = compute_supplier_stats(df_current)
        if not stats.empty:
            fig = px.bar(stats, x='Себестоимость', y='Поставщик', orientation='h')
            st.plotly_chart(ui.update_chart_layout(fig), use_container_width=True)

def render_menu(df_current, df_prev, current_label="", prev_label=""):
    view_mode = st.radio("Вид:", ["Макро", "Микро"], horizontal=True, label_visibility="collapsed")
    target_cat = 'Макро_Категория' if view_mode == "Макро" else 'Категория'
    
    cats, items = compute_menu_tab_data(df_current, target_cat)
    
    c1, c2 = st.columns([1, 1.5])
    with c1:
        fig = px.pie(cats, values='Выручка с НДС', names=target_cat, hole=0.45, title="Структура выручки")
        st.plotly_chart(ui.update_chart_layout(fig), use_container_width=True)
    with c2:
        st.dataframe(
            items[['Выручка с НДС', 'Себестоимость', 'Фудкост %', 'Количество']],
            column_config={
                "Выручка с НДС": st.column_config.NumberColumn(format="%.0f ₽"),
                "Фудкост %": st.column_config.NumberColumn(format="%.1f %%"),
            },
            use_container_width=True,
            height=400
        )

    if not df_prev.empty:
        cats_prev, _ = compute_menu_tab_data(df_prev, target_cat)
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
    abc, aq, am = compute_abc_data(df_current)
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
            res = compute_simulation(df_current, sel_cats, d_price, d_cost, d_vol)
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
    daily_cur, weekday_cur = compute_weekday_stats(df_current)
    if weekday_cur.empty:
        st.info("Нет данных для анализа дней недели.")
        return

    c1, c2 = st.columns(2)
    with c1:
        if not df_prev.empty:
            _, weekday_prev = compute_weekday_stats(df_prev)
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
            daily_prev, _ = compute_weekday_stats(df_prev)
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
