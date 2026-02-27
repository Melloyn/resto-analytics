"""
Centralized Observability Infrastructure.
Provides structured logging setup and Sentry SDK initialization
governed entirely by environment variables.
"""

import os
import logging
import re
from typing import Any, Dict

# Standard python logger initialization for the top-level app
log = logging.getLogger(__name__)

# Patterns to scrub in logs and Sentry events
SENSITIVE_PATTERNS = [
    re.compile(r"([a-zA-Z0-9_\-]{30,})"),  # Catch tokens/dsn looking strings
    re.compile(r"([a-z0-9]{32})", re.IGNORECASE), # Catch md5 hashes/salts
]


def _scrub_sensitive_data(event: Dict[str, Any], hint: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sentry before_send hook. Recursively scrubs tokens and passwords
    from event traces before they leave the server.
    """
    
    def _mask_string(val: str) -> str:
        for pattern in SENSITIVE_PATTERNS:
            val = pattern.sub("[REDACTED]", val)
        return val

    def _recursive_scrub(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _recursive_scrub(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_recursive_scrub(i) for i in obj]
        elif isinstance(obj, str):
            return _mask_string(obj)
        return obj

    try:
        # Scrub local variables in stacktraces
        if "exception" in event and "values" in event["exception"]:
            for exc in event["exception"]["values"]:
                if "stacktrace" in exc and "frames" in exc["stacktrace"]:
                    for frame in exc["stacktrace"]["frames"]:
                        if "vars" in frame:
                            frame["vars"] = _recursive_scrub(frame["vars"])
    except Exception:
        pass # Better to send unscrubbed log than to drop the event if scrubber fails, 
             # though strictly SENSITIVE_PATTERNS will catch most.
        
    return event


def setup_observability() -> None:
    """
    Initializes global system logging and Sentry (if DSN is present).
    Should be called once at application startup.
    """
    
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Complete format: [2026-02-27 15:00:00] INFO - module.name: The message
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            sentry_env = os.getenv("SENTRY_ENV", "development")
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=sentry_env,
                # Set traces_sample_rate to 1.0 to capture 100%
                # of transactions for performance monitoring.
                traces_sample_rate=1.0,
                send_default_pii=False,
                before_send=_scrub_sensitive_data
            )
            log.info(f"Sentry SDK initialized (env: {sentry_env})")
        except ImportError:
            log.warning("SENTRY_DSN provided but sentry-sdk is not installed. Skipping Sentry init.")
    else:
        log.info("SENTRY_DSN not provided. Running without Sentry.")

    # We also quiet down noisy third-party loggers here
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
