def test_use_cases_modules_import() -> None:
    import use_cases  # noqa: F401
    from use_cases import auth_flow, bootstrap  # noqa: F401

