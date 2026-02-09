import unittest
from datetime import datetime

import pandas as pd

from processing import detect_category_granular, detect_header_row, parse_russian_date


class ProcessingTests(unittest.TestCase):
    def test_parse_russian_date_text(self):
        parsed = parse_russian_date("Отчет за 15 марта 2024")
        self.assertEqual(parsed, datetime(2024, 3, 15))

    def test_detect_header_row(self):
        df_preview = pd.DataFrame([
            ["", ""],
            ["Дата", "Что-то"],
            ["Блюдо", "Выручка с НДС"],
        ])
        self.assertEqual(detect_header_row(df_preview, "Выручка с НДС"), 2)

    def test_manual_category_override(self):
        self.assertEqual(detect_category_granular("джин-тоник"), "🍹 Коктейли")


if __name__ == "__main__":
    unittest.main()
