import io
import pandas as pd
from services import parsing_service


def _build_turnover_like_df():
    rows = []
    # header row (finds "Номенклатура" and "Дебет")
    rows.append(["Номенклатура", "", "", "", "Дебет", "Кредит", "Кон.остаток"])
    # main item row name is previous row, and next row has marker "Кол." in column B
    rows.append(["Сахар", "", "кг", "", "", "", ""])
    rows.append(["", "Кол.", "", "", 5, 2, 10])
    # history row
    rows.append(["Обороты за 11.02.26", "", "", "", "", "", ""])
    rows.append(["", "Кол.", "", "", 0, 1.5, 0])
    # another item
    rows.append(["Молоко", "", "л", "", "", "", ""])
    rows.append(["", "Кол.", "", "", 2, 3, 7])
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, header=False)
    buf.seek(0)
    return buf


def test_parse_turnover_basic():
    buf = _build_turnover_like_df()
    df_stock, df_hist, err = parsing_service.parse_turnover(buf, "turnover.xlsx")
    assert err is None
    assert df_stock is not None
    assert not df_stock.empty
    assert "ingredient" in df_stock.columns
    assert "stock_qty" in df_stock.columns
    # should parse 2 items
    assert df_stock.shape[0] >= 2
    # history should have one row
    assert df_hist is not None
    assert df_hist.shape[0] == 1


def _build_ttk_like_df():
    rows = []
    rows.append(["Наименование блюда", "Суп дня"])
    rows.append(["Наименование продукта", "Бульон", "", "", "", "", "", "", "", "", "", "", "", "", 0.5, "л"])
    rows.append(["", "Морковь", "", "", "", "", "", "", "", "", "", "", "", "", 0.1, "кг"])
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, header=False)
    buf.seek(0)
    return buf


def test_parse_ttk_basic():
    buf = _build_ttk_like_df()
    res, err = parsing_service.parse_ttk(buf, "ttk.xlsx")
    assert err is None
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]["dish_name"] == "суп дня"
    assert len(res[0]["ingredients"]) >= 1
