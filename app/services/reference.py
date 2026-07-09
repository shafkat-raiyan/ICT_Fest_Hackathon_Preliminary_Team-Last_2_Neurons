"""Human-facing booking reference codes.

Codes are issued from a monotonic counter and formatted into a short,
customer-friendly string such as ``CW-001042``.
"""
import itertools
import threading

_lock = threading.Lock()
_counter = itertools.count(1000)


def next_reference_code() -> str:
    with _lock:
        current = next(_counter)
    return f"CW-{current:06d}"
