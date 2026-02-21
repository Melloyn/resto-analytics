import streamlit as st
import pandas as pd
import logging
from io import BytesIO
import telegram_utils

logger = logging.getLogger(__name__)

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
