"""Report context preparation for application layer orchestration."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

import pandas as pd


@dataclass(frozen=True)
class ReportContext:
    """Prepared data context for report rendering."""

    df_current: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_prev: pd.DataFrame = field(default_factory=pd.DataFrame)
    current_label: str = ""
    prev_label: str = ""
    selected_period: dict[str, Any] = field(default_factory=dict)


def build_report_context(
    df_full: Optional[pd.DataFrame],
    period_mode: str,
    *,
    selected_ym: Any = None,
    scope_mode: str = "Весь месяц",
    selected_day: Optional[int] = None,
    compare_mode: str = "Год назад",
    date_range: Optional[Tuple[Any, Any]] = None,
    now: Optional[datetime] = None,
) -> ReportContext:
    """Build report DataFrame slices and labels from selected period parameters."""
    if df_full is None or df_full.empty:
        return ReportContext()

    if period_mode == "📌 Последний загруженный день":
        last_day = pd.to_datetime(df_full["Дата_Отчета"]).max().normalize()
        day_start = last_day
        day_end = last_day + timedelta(hours=23, minutes=59, seconds=59)
        df_current = df_full[(df_full["Дата_Отчета"] >= day_start) & (df_full["Дата_Отчета"] <= day_end)]
        return ReportContext(
            df_current=df_current,
            df_prev=pd.DataFrame(),
            current_label=f"{last_day.strftime('%d.%m.%Y')} (последний загруженный день)",
            prev_label="",
            selected_period={
                "start": day_start,
                "end": day_end,
                "days": 1,
                "inflation_start": day_start.replace(day=1),
            },
        )

    if period_mode == "📅 Месяц (Сравнение)":
        if selected_ym is None:
            return ReportContext()

        start_cur = selected_ym.start_time
        end_cur = selected_ym.end_time
        if scope_mode == "По конкретный день":
            if selected_day is None:
                reference_dt = now or datetime.now()
                max_d = int(selected_ym.to_timestamp(how="end").day)
                selected_day = min(reference_dt.day, max_d)
            end_cur = start_cur + timedelta(days=selected_day - 1)
            end_cur = end_cur.replace(hour=23, minute=59, second=59)

        df_current = df_full[(df_full["Дата_Отчета"] >= start_cur) & (df_full["Дата_Отчета"] <= end_cur)]
        df_prev = pd.DataFrame()
        prev_label = ""

        if compare_mode == "Предыдущий месяц":
            prev_ym = selected_ym - 1
            start_prev = prev_ym.start_time
            end_prev = start_prev + (end_cur - start_cur)
            df_prev = df_full[(df_full["Дата_Отчета"] >= start_prev) & (df_full["Дата_Отчета"] <= end_prev)]
            prev_label = prev_ym.strftime("%b %Y")
        elif compare_mode == "Год назад":
            prev_ym = selected_ym - 12
            start_prev = prev_ym.start_time
            end_prev = start_prev + (end_cur - start_cur)
            df_prev = df_full[(df_full["Дата_Отчета"] >= start_prev) & (df_full["Дата_Отчета"] <= end_prev)]
            prev_label = prev_ym.strftime("%b %Y")

        return ReportContext(
            df_current=df_current,
            df_prev=df_prev,
            current_label=f"{selected_ym.strftime('%b %Y')} ({scope_mode})",
            prev_label=prev_label,
            selected_period={
                "start": start_cur,
                "end": end_cur,
                "days": (end_cur - start_cur).days + 1,
                "inflation_start": start_cur,
            },
        )

    if period_mode == "📆 Диапазон" and isinstance(date_range, tuple) and len(date_range) == 2:
        start_raw, end_raw = date_range
        start_dt = pd.to_datetime(start_raw)
        end_dt = pd.to_datetime(end_raw) + timedelta(hours=23, minutes=59)
        df_current = df_full[(df_full["Дата_Отчета"] >= start_dt) & (df_full["Дата_Отчета"] <= end_dt)]
        return ReportContext(
            df_current=df_current,
            df_prev=pd.DataFrame(),
            current_label=f"{start_dt.date()} - {end_dt.date()}",
            prev_label="",
            selected_period={
                "start": start_dt,
                "end": end_dt,
                "days": (end_dt - start_dt).days + 1,
                "inflation_start": start_dt,
            },
        )

    return ReportContext()
