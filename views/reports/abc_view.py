import streamlit as st
import plotly.express as px
import ui
from services import analytics_service

def render_abc(df_current):
    placeholder = st.empty()
    with placeholder.container():
        ui.render_skeleton_chart()
        import time; time.sleep(0.01)

    abc, aq, am = analytics_service.compute_abc_data(df_current)
    
    placeholder.empty()
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
            height=500,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Выручка": st.column_config.NumberColumn("Выручка", format="%d ₽"),
                "С/С": st.column_config.NumberColumn("С/С", format="%d ₽"),
                "Кол-во": st.column_config.NumberColumn("Кол-во", format="%d"),
                "Маржа/шт": st.column_config.NumberColumn("Маржа/шт", format="%d ₽"),
            }
        )
