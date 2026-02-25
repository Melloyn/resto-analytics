# 2. Session Facade

* Status: Accepted
* Date: 2026-02-25

## Context and Problem Statement
Streamlit's `st.session_state` allows global, dictionary-like access to application state. Historically, components across all layers were reading and writing to `st.session_state` arbitrarily. This led to "race conditions," lack of type safety, and made testing pure functions nearly impossible because they implicitly depended on the Streamlit context.

## Decision
We centralized all interaction with `st.session_state` into a single module: `utils/session_manager.py`.

* Direct access to `st.session_state` outside of `session_manager.py` (for core state) is considered an anti-pattern.
* `session_manager.py` acts as a Typed Facade, ensuring all required keys are initialized (see "Session State Contract" in README).
* The Application Layer (`use_cases/`) interacts with the Session Manager to retrieve typed objects (e.g., `UserSession` DTO) and returns statuses/DTOs to `app.py`.
* `use_cases/` deliberately avoids calling `st.stop()` or rendering UI directly, ensuring orchestration is separated from presentation. It returns execution flow flags (e.g., `STOP` or `CONTINUE`).

## Consequences
* **Positive**: State becomes predictable and typical. Tests can easily mock the state by injecting data into `st.session_state` before calling use cases. Avoids "Missing ScriptRunContext" errors in unit tests.
* **Negative**: All new global state variables must be explicitly defined and initialized in `session_manager.init_session_state()`.

## Alternatives considered
* Passing state explicitly as function arguments everywhere (rejected because Streamlit apps often have deep component trees where prop-drilling becomes tedious).
* Using experimental third-party session state libraries for Streamlit (rejected in favor of a simple, native facade).

## Links
* Related to README section "Контракт состояния" (Session State Contract).
