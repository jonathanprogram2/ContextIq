"""Single-process login throttling for local development."""

import math
import threading
import time

from fastapi import HTTPException

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60

_lock = threading.Lock()
_failures: dict[tuple[str, str], list[float]] = {}


def check_limit(key: tuple[str, str]) -> None:
    now = time.monotonic()

    with _lock:
        # Remove stale entries to keep memory bounded over time.
        for existing_key in list(_failures):
            recent = [
                t for t in _failures[existing_key]
                if now - t < WINDOW_SECONDS
            ]
            if recent:
                _failures[existing_key] = recent
            else:
                del _failures[existing_key]

        attempts = _failures.get(key, [])

        if len(attempts) >= MAX_FAILURES:
            retry_after = max(
                1,
                math.ceil(WINDOW_SECONDS - (now - attempts[0])),
            )
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )


def record_failure(key: tuple[str, str]) -> None:
    with _lock:
        _failures.setdefault(key, []).append(time.monotonic())


def clear_failures(key: tuple[str, str]) -> None:
    with _lock:
        _failures.pop(key, None)