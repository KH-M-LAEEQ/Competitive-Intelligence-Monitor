import time
from collections import defaultdict
from threading import Lock

__all__ = ["RateLimitExceededError", "check_rate_limit", "reset_rate_limits"]


class RateLimitExceededError(Exception):
    pass


# In-process, single-instance limiter (same project decision and caveat as
# app/scheduler.py) — a fixed window per key, not a sliding log or token
# bucket, since "simple" is the explicit requirement here. Running more than
# one app process/replica would let each process allow its own quota rather
# than sharing one; a Redis-backed limiter would be the fix if this ever
# needs to scale horizontally.
_lock = Lock()
_hits: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(key: str, limit: int, window_seconds: float) -> None:
    now = time.monotonic()

    with _lock:
        timestamps = _hits[key]
        cutoff = now - window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        if len(timestamps) >= limit:
            raise RateLimitExceededError(
                f"Rate limit exceeded: {limit} requests per {window_seconds:.0f}s"
            )

        timestamps.append(now)


def reset_rate_limits() -> None:
    """Test-only hook. Each pytest run creates a fresh in-memory DB per test
    (see conftest.py) so workspace ids restart at 1 every test — without
    resetting this module-level state too, an unrelated earlier test's hits
    against workspace 1 would leak into the next test's rate-limit count.
    """
    with _lock:
        _hits.clear()
