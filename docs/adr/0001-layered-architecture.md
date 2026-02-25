# 1. Layered Architecture

* Status: Accepted
* Date: 2026-02-25

## Context and Problem Statement
The application previously suffered from tightly coupled code, where UI (`views/`, `app.py`), business logic, and infrastructure details (`sqlite3`, `requests`) were interwoven. This made testing difficult, increased the risk of regressions, and hindered scalability.

## Decision
We adopted a layered architecture (inspired by Clean Architecture/Hexagonal Architecture) to separate concerns:

* **Presentation (`views/`, `ui.py`)**: Responsible solely for rendering Streamlit components.
* **Application (`use_cases/`, `app.py`)**: Orchestrates the flow of data between UI and services.
* **Domain (`services/`)**: Contains pure business logic (calculations, KPI derivations).
* **Infrastructure (`infrastructure/`)**: Contains adapters for external systems (Database, Yandex Disk, Telegram).
* **Utils (`utils/`)**: Contains cross-cutting concerns like `session_manager` acting as a facade for Streamlit state.

**Allowed Dependencies:**
* `app.py` -> `use_cases/` -> `services/`, `infrastructure/`, `utils/`.
* `views/` -> Consumes logic from `app.py` and `use_cases/` via DTOs/ViewModels. No direct IO.

**Forbidden Dependencies (Enforced via `ruff.toml` `flake8-tidy-imports` `BANNED_API`):**
* `services/` -> `streamlit`, `sqlite3`, `views/`, `use_cases/`.
* `infrastructure/` -> `streamlit`, `views/`, `use_cases/`.
(Exceptions for `streamlit` exist only in `utils/` and `tests/` when absolutely necessary, and naturally in UI layers).

## Consequences
* **Positive**: Business logic is easily unit-testable without Streamlit context. Infrastructure can be swapped (e.g., from SQLite to Postgres) without touching views or domain logic.
* **Negative**: Requires more boilerplate (DTOs, interfaces) to pass data between layers.

## Alternatives considered
* Keeping everything in "God objects" like `app.py` (rejected due to unmaintainability).
* Using a heavy framework like Django/FastAPI alongside Streamlit (rejected to keep deployment simple and avoid zero-downtime concerns).

## Links
* Related to: [Enterprise Strategy Modernization Roadmap]
