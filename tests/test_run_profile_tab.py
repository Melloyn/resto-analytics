import os
from unittest.mock import patch

os.environ["DEBUG_TIMINGS"] = "1"
os.environ["YANDEX_TOKEN"] = ""

from streamlit.testing.v1 import AppTest
from use_cases.report_flow import REPORT_TAB_LABELS

class MockUser:
    id = "profiler_mock"
    role = "admin"
    login = "admin_mock"
    full_name = "Profiler Admin"

class MockAuthResult:
    status = "CONTINUE"

print("\n--- MEASURING TABS (MOCKED AUTH & STARTUP) ---")

with patch("use_cases.bootstrap.run_startup") as mock_startup:
    mock_startup_ret = lambda: type("MockStartupRes", (), {"status": "CONTINUE", "planned_steps": ()})
    mock_startup.return_value = mock_startup_ret()
    
    with patch("use_cases.auth_flow.ensure_authenticated_session") as mock_auth:
        mock_auth.return_value = MockAuthResult()
        
        at = AppTest.from_file("app.py", default_timeout=40)
        at.session_state["auth_user"] = MockUser()
        at.session_state["is_admin"] = False
        at.session_state["admin_fullscreen"] = False
        at.session_state["dropped_stats"] = {"count": 0}
        at.session_state["edit_yandex_path"] = False
        at.session_state["yandex_path"] = "RestoAnalytic"
        
        import pandas as pd
        import numpy as np
        
        at.session_state["df_full"] = pd.DataFrame({
            'Дата_Отчета': pd.date_range(start='2026-01-01', periods=100),
            'Блюдо': ['Dish A', 'Dish B'] * 50,
            'Выручка с НДС': np.random.rand(100) * 1000,
            'Себестоимость': np.random.rand(100) * 300,
            'Количество': np.random.randint(1, 10, 100),
            'Категория': ['Food', 'Drink'] * 50,
            'Макро_Категория': ['Kitchen', 'Bar'] * 50,
            'Точка': ['Venue 1', 'Venue 1'] * 50,
            'Unit_Cost': np.random.rand(100) * 100,
            'Поставщик': ['Supplier A', 'Supplier B'] * 50,
            'Фудкост': np.random.rand(100) * 30
        })
        
        at.run()
        
        for tab in REPORT_TAB_LABELS:
            print(f"\nRunning Tab: {tab}")
            try:
                at.session_state["nav_tab"] = tab
                at.run()
            except Exception as e:
                print(f"Failed to render {tab}: {e}")
            if "profiling_data" in at.session_state:
                for p in at.session_state["profiling_data"]:
                    if p["step"].startswith("Render Route"):
                        print(f"  {p['step']}: {p['duration_ms']:.2f} ms")
            else:
                print("  profiling_data not in session state")
