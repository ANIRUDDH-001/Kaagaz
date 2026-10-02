"""Protects the free Gemma quota (30 requests and 16k tokens a minute) from one busy demo visitor."""
import time
from collections import deque


class HourlyLimiter:
    def __init__(self, limit: int = 15, window: float = 3600.0, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self.hits: dict[str, deque] = {}

    def allow(self, key: str) -> bool:
        now = self.clock()
        q = self.hits.setdefault(key, deque())
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
