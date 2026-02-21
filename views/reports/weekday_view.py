import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import ui
from services import analytics_service

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
