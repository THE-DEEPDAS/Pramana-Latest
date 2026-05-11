from __future__ import annotations

import threading
import time


class SharedRateLimiter:
    def __init__(self, requests_per_minute: int):
        self._min_interval = 60.0 / max(1, requests_per_minute)
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_seconds = self._min_interval - (now - self._last_call)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            self._last_call = time.monotonic()


NVIDIA_RATE_LIMITER = SharedRateLimiter(requests_per_minute=40)
