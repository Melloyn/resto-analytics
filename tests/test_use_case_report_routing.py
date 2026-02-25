from use_cases import report_flow


def test_select_report_route_maps_known_labels() -> None:
    assert report_flow.select_report_route("Выручка (Меню)") == report_flow.ReportRoute.MENU
    assert report_flow.select_report_route("Инфляция С/С") == report_flow.ReportRoute.INFLATION
    assert report_flow.select_report_route("ABC-анализ") == report_flow.ReportRoute.ABC
    assert report_flow.select_report_route("Симулятор цен") == report_flow.ReportRoute.SIMULATOR
    assert report_flow.select_report_route("Дни недели") == report_flow.ReportRoute.WEEKDAYS
    assert report_flow.select_report_route("Закупки") == report_flow.ReportRoute.PROCUREMENT


def test_select_report_route_uses_menu_fallback_for_unknown_label() -> None:
    assert report_flow.select_report_route("UNKNOWN_ROUTE") == report_flow.ReportRoute.MENU
