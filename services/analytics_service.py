import pandas as pd
from datetime import timedelta


def compute_inflation_metrics(df_scope, df_v):
    if df_scope.empty or df_v.empty:
        return 0, 0, pd.DataFrame()
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
    if 'Поставщик' not in df.columns or df.empty:
        return pd.DataFrame()
    return (
        df.groupby('Поставщик')['Себестоимость']
        .sum()
        .reset_index()
        .sort_values('Себестоимость', ascending=False)
        .head(15)
    )


def compute_menu_tab_data(df, group_col):
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    cat_df = (
        df.groupby(group_col)['Выручка с НДС']
        .sum()
        .reset_index()
        .sort_values(by='Выручка с НДС', ascending=False)
    )

    menu_df = df.groupby('Блюдо').agg({
        'Выручка с НДС': 'sum',
        'Себестоимость': 'sum',
        'Количество': 'sum'
    }).reset_index()
    menu_df['Фудкост %'] = (menu_df['Себестоимость'] / menu_df['Выручка с НДС'] * 100).fillna(0)
    menu_df = menu_df.sort_values('Выручка с НДС', ascending=False)
    return cat_df, menu_df


def compute_abc_data(df):
    if df.empty:
        return pd.DataFrame(), 0, 0
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
        if high_vol and high_prof:
            return "⭐ Звезда"
        if high_vol and not high_prof:
            return "🐎 Лошадка"
        if not high_vol and high_prof:
            return "❓ Загадка"
        return "🐶 Собака"

    abc['Класс'] = abc.apply(classify, axis=1)
    return abc, avg_qty, avg_margin


def compute_weekday_stats(df):
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    ru_days = {
        0: 'Понедельник', 1: 'Вторник', 2: 'Среда', 3: 'Четверг',
        4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
    }

    daily = df.groupby('Дата_Отчета')['Выручка с НДС'].sum().reset_index()
    daily['ДеньРус'] = daily['Дата_Отчета'].dt.weekday.map(ru_days)
    daily['Дата_Подпись'] = daily['Дата_Отчета'].dt.strftime('%d.%m')

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
    if df.empty:
        return pd.DataFrame(columns=['Budget'])
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
    if df.empty:
        return None
    mask = df['Категория'].isin(cats)
    target = df[mask].copy()
    other = df[~mask].copy()

    base_rev = df['Выручка с НДС'].sum()
    base_cost = df['Себестоимость'].sum()
    base_margin = base_rev - base_cost

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
