"""Request-local time budget for serverless analysis."""
from contextlib import contextmanager
from contextvars import ContextVar
import time

_deadline = ContextVar('finn_deadline', default=None)


@contextmanager
def limit(seconds):
    token = _deadline.set(time.monotonic() + seconds)
    try:
        yield
    finally:
        _deadline.reset(token)


def remaining():
    deadline = _deadline.get()
    return float('inf') if deadline is None else max(0, deadline - time.monotonic())


def timeout(maximum):
    seconds = min(maximum, remaining())
    if seconds < 1:
        raise TimeoutError('Analysis reached the hosting time limit. Retry to reuse cached extraction, or run locally for a larger research budget.')
    return seconds
