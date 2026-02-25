import pandas as pd

from use_cases import report_flow


def _make_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Дата_Отчета": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-02-01",
                    "2026-02-02",
                    "2026-02-03",
                ]
            ),
            "Выручка с НДС": [10, 20, 30, 40, 50, 60],
            "Себестоимость": [3, 4, 5, 6, 7, 8],
            "Количество": [1, 2, 3, 4, 5, 6],
            "Блюдо": ["A", "A", "B", "A", "B", "C"],
        }
    )


def test_build_report_context_returns_valid_context_for_last_day() -> None:
    df_full = _make_df()
    ctx = report_flow.build_report_context(df_full, "📌 Последний загруженный день")

    assert isinstance(ctx, report_flow.ReportContext)
    assert not ctx.df_current.empty
    assert ctx.df_prev.empty
    assert ctx.current_label.endswith("(последний загруженный день)")
    assert ctx.selected_period["days"] == 1


def test_build_report_context_forms_month_labels() -> None:
    df_full = _make_df()
    selected_ym = pd.Period("2026-02", freq="M")
    ctx = report_flow.build_report_context(
        df_full,
        "📅 Месяц (Сравнение)",
        selected_ym=selected_ym,
        scope_mode="Весь месяц",
        compare_mode="Предыдущий месяц",
    )

    assert ctx.current_label == f"{selected_ym.strftime('%b %Y')} (Весь месяц)"
    assert ctx.prev_label == (selected_ym - 1).strftime("%b %Y")
    assert ctx.selected_period["days"] >= 28


def test_build_report_context_handles_none_df() -> None:
    ctx = report_flow.build_report_context(None, "📌 Последний загруженный день")
    assert isinstance(ctx, report_flow.ReportContext)
    assert ctx.df_current.empty
    assert ctx.df_prev.empty
    assert ctx.current_label == ""
    assert ctx.selected_period == {}
