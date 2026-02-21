import streamlit as st
import ui
from services import analytics_service, data_loader

def render_simulator(df_current, df_full):
    st.header("🧪 Симулятор роста цен (Ингредиенты)")
    st.info("Выберите ингредиенты, укажите рост цены (в рублях за единицу), и увидите, как это повлияет на себестоимость блюд.")
    
    recipes_db = data_loader.get_recipes_map()
    if not recipes_db:
        st.warning("⚠️ Нет данных о рецептах (ТТК). Загрузите файлы TechnologicalMaps.")
        return

    all_ingredients = analytics_service.get_unique_ingredients(recipes_db)
    
    # UI: Ingredient Selection
    selected_ingredients = st.multiselect(
        "Выберите ингредиенты для симуляции:", 
        options=all_ingredients
    )
    
    if selected_ingredients:
        st.subheader("Настройка роста цен (₽)")
        cols = st.columns(3)
        ingredient_deltas = {}
        
        for idx, ing in enumerate(selected_ingredients):
            with cols[idx % 3]:
                delta = st.number_input(
                    f"Рост для '{ing}' (₽):", 
                    min_value=0.0, 
                    value=0.0, 
                    step=1.0, 
                    key=f"sim_delta_{idx}"
                )
                if delta > 0:
                    ingredient_deltas[ing] = delta
        
        if ingredient_deltas:
            st.divider()
            if st.button("🚀 Рассчитать влияние", type="primary"):
                # We use df_current for current costs and layout
                sim_results = analytics_service.simulate_forecast(recipes_db, ingredient_deltas, df_current)
                
                if sim_results.empty:
                    st.warning("Не найдено блюд, использующих эти ингредиенты (среди текущих продаж).")
                else:
                    st.subheader("📊 Результаты симуляции")
                    
                    # Totals
                    total_increase = (sim_results['Рост с/с'] * sim_results['Количество']).sum()
                    st.metric("Общий рост себестоимости (на текущий объем продаж)", f"{total_increase:,.0f} ₽")
                    
                    # Table
                    sim_view = sim_results.sort_values('Рост с/с', ascending=False).rename(columns={
                        "Текущая с/с": "Текущая с/с",
                        "Рост с/с": "Рост (+)",
                        "Новая с/с": "Новая с/с",
                        "Количество": "Продажи (шт)"
                    })
                    ui.render_aggrid(
                        sim_view,
                        height=400,
                        pagination=True,
                        formatting={
                            "Текущая с/с": "%.2f ₽",
                            "Рост (+)": "%.2f ₽",
                            "Новая с/с": "%.2f ₽",
                            "Продажи (шт)": "%.0f"
                        }
                    )
        else:
            st.info("Укажите рост цены хотя бы для одного ингредиента.")
    else:
        st.markdown("Use the multiselect above to add ingredients.")
