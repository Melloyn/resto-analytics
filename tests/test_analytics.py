import pytest
import pandas as pd
import numpy as np

from services.analytics_service import calculate_insights, compute_abc_data

@pytest.fixture
def sample_curr_df():
    return pd.DataFrame({
        'Блюдо': ['Burger', 'Fries', 'Cola', 'Salad'],
        'Количество': [100, 200, 150, 10],
        'Выручка с НДС': [50000.0, 20000.0, 15000.0, 3000.0],
        'Себестоимость': [15000.0, 5000.0, 3000.0, 2500.0],
        'Unit_Cost': [150.0, 25.0, 20.0, 250.0]
    })

@pytest.fixture
def sample_prev_df():
    return pd.DataFrame({
        'Блюдо': ['Burger', 'Fries', 'Cola', 'DogItem'],
        'Количество': [90, 180, 140, 5],
        'Выручка с НДС': [45000.0, 18000.0, 14000.0, 1000.0],
        'Себестоимость': [13500.0, 4500.0, 2800.0, 800.0],
        'Unit_Cost': [150.0, 25.0, 15.0, 160.0]  # Cola was 15, now 20 => 33% inflation
    })

def test_calculate_insights_revenue_growth(sample_curr_df, sample_prev_df):
    cur_rev = sample_curr_df['Выручка с НДС'].sum()
    prev_rev = sample_prev_df['Выручка с НДС'].sum()
    cur_fc = 30.0  # target is 35.0, so this is good
    
    insights = calculate_insights(sample_curr_df, sample_prev_df, cur_rev, prev_rev, cur_fc)
    
    types = [i.type for i in insights]
    assert 'inflation' in types, "Should detect 33% inflation on Cola"
    assert 'high_fc' not in types, "FC is <= 35, should not warn"
    # Rev growth: current is 88000, prev is 78000. Diff = 12.8%. It won't trigger > 20% or < -10%. 
    assert 'rev_growth' not in types
    assert 'rev_drop' not in types

def test_calculate_insights_dogs(sample_curr_df, sample_prev_df):
    # Add many dead items to trigger "dogs" alert
    dogs_df = pd.DataFrame({
        'Блюдо': [f'Dog_{i}' for i in range(10)],
        'Количество': [1] * 10,
        'Выручка с НДС': [100.0] * 10,
        'Себестоимость': [90.0] * 10,
        'Unit_Cost': [90.0] * 10
    })
    curr_combined = pd.concat([sample_curr_df, dogs_df])
    
    insights = calculate_insights(curr_combined, sample_prev_df, curr_combined['Выручка с НДС'].sum(), 100000.0, 30.0)
    types = [i.type for i in insights]
    
    assert 'dogs' in types, "Should detect multiple 'Dog' items"
    assert 'rev_drop' in types, "Revenue dropped from 100,000 to ~89,000"

def test_compute_abc_data(sample_curr_df):
    abc, avg_qty, avg_margin = compute_abc_data(sample_curr_df)
    
    assert not abc.empty
    assert 'Класс' in abc.columns
    
    # Fries: vol=200, margin=15k => Unit_margin = 75
    # Burger: vol=100, margin=35k => Unit_margin = 350
    # Avg_qty = (100+200+150+10)/4 = 115
    # Fries is High Vol, Low-ish margin -> '🐎 Лошадка' or 'Собака' depending on avg 
    
    fries_class = abc[abc['Блюдо'] == 'Fries'].iloc[0]['Класс']
    # Just check it computes without crashing and assigns a class
    assert "⭐" in fries_class or "🐎" in fries_class or "🐶" in fries_class or "❓" in fries_class

def test_compute_abc_empty():
    abc, avg_qty, avg_margin = compute_abc_data(pd.DataFrame())
    assert abc.empty
    assert avg_qty == 0
    assert avg_margin == 0
