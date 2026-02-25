import streamlit as st
import pandas as pd
from datetime import timedelta
import ui
from use_cases.session_models import is_admin
from services import data_loader, parsing_service

def render_procurement_v2(df_sales, df_full, period_days):
    placeholder = st.empty()
    with placeholder.container():
        ui.render_skeleton_chart()
        import time; time.sleep(0.01)

    st.subheader("📦 План Закупок (Smart)")
    
    placeholder.empty()

    recipes_map = data_loader.get_recipes_map()
    stock_df = data_loader.get_stock_data()

    admin_mode = False
    if st.session_state.get('auth_user') and is_admin(st.session_state.auth_user):
        admin_mode = True
    elif st.session_state.get('is_admin'):
        admin_mode = True

    # --- DEBUG SECTION (ADMIN ONLY) ---
    if admin_mode:
        with st.expander("🕵️ Диагностика Белого Списка (Что есть в Товарообороте?)"):
            st.write(f"Всего позиций в Товарообороте: {len(stock_df) if stock_df is not None else 0}")
            if stock_df is not None:
                search_term = st.text_input("Поиск по Товарообороту:", value="рислинг")
                if search_term:
                    debug_hits = stock_df[stock_df['ingredient'].str.contains(search_term, case=False, na=False)]
                    ui.render_aggrid(debug_hits[['ingredient', 'unit', 'stock_qty']], height=300)
                else:
                    ui.render_aggrid(stock_df[['ingredient', 'unit', 'stock_qty']].head(10), height=300)
    
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

    # Defaults
    lead_time = 3
    trend_window_days = 28
    ly_window_days = 14
    sigma_window_days = 56
    service_level = 95
    holiday_boost = 20
    trend_weight = 0.6
    ly_weight = 0.4
    use_weekday_yoy = True
    yoy_cap = 1.5
    pack_size_default = 0.0
    min_order_default = 0.0
    holiday_text = ""

    preset_mode = "Авто (рекомендуется)"
    
    if admin_mode:
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
        df_history = data_loader.get_turnover_history()
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

        # Prepare Validation Set (Strict Whitelist from Stock/Turnover)
        valid_stock_items = set()
        if stock_df is not None and not stock_df.empty:
             valid_stock_items = set(stock_df['ingredient'].unique())

        def explode_sales_to_ingredients(df_src):
            if df_src.empty:
                return pd.DataFrame(columns=["date", "ingredient", "qty"])
            df_src = df_src.copy()
            
            # Group by dish
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
                    # NO RECIPE found.
                    # STRICT CHECK: Only keep if it exists in Stock (Turnover) file.
                    if name in valid_stock_items:
                        rows.append({"date": dt, "ingredient": name, "qty": qty_needed})
                    # Else: Drop it (Virtual Dish, Modifier, Service, etc.)

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
                    # 1. Exclude items that have recipes (they are composite dishes)
                    df_hist_ing = df_hist_ing[~df_hist_ing['ingredient'].isin(recipes_map.keys())]
                    
                    # 2. Strict Whitelist Check for History too
                    if not df_hist_ing.empty and valid_stock_items:
                        df_hist_ing = df_hist_ing[df_hist_ing['ingredient'].isin(valid_stock_items)]

                    if not df_hist_ing.empty:
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
        "Остаток": "%.2f",
        "Хватит (дней)": "%.0f",
        "Закупить": "%.2f",
        "Ср. расход/день": "%.2f",
        "Прогноз/день": "%.2f",
        "Прошлый год": "%.2f",
        "Праздн. коэф.": "%.2f"
    }
    if "Умный" in forecast_method:
        format_dict[trend_label] = "%.2f"
        
    ui.render_aggrid(
        df_display,
        height=600,
        pagination=True,
        formatting=format_dict
    )
