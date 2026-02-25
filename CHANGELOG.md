# Changelog

## v0.2.6 - 2026-02-25

- docs: add README/runbook and integration guard test
- Added Application layer skeleton in `use_cases/` (`__init__`, `auth_flow`, `bootstrap`) with typed contracts.
- Moved auth gate orchestration from `app.py` to `use_cases/auth_flow.py` (`init -> restore -> gate -> validate`) without UI behavior changes.
- Moved startup/bootstrap + autosync orchestration from `app.py` to `use_cases/bootstrap.py` while preserving side-effect order and session-flag idempotency.
- Added/updated tests for `use_cases` contracts and orchestration paths (`auth_flow`, `bootstrap`).
