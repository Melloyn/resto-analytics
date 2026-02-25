import pytest
from services.category_service import detect_category_granular

def test_detect_category_granular_from_mapping():
    # It should prioritize explicit mapping
    mapping = {
        'Кальян на фрукте': '🍷 Вино', # bizarre mapping but proves priority
        'Кофе американо': '☕ Кофе'
    }
    cat = detect_category_granular('Кальян на фрукте', mapping)
    assert cat == '🍷 Вино'
    
    cat2 = detect_category_granular('Кофе американо', mapping)
    assert cat2 == '☕ Кофе'

def test_detect_category_granular_fallback():
    # If not in mapping and not triggering keywords exactly
    cat = detect_category_granular('Неведомое блюдо 123', {})
    assert cat == '📦 Прочее'

def test_detect_category_normalization():
    mapping = {'burger': '🍔 Еда (Кухня)'}
    # It normalizes input to lowercase
    cat = detect_category_granular(' BURGER ', mapping)
    assert cat == '🍔 Еда (Кухня)'
