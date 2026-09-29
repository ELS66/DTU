"""Development retry schedule for durable telemetry acknowledgements."""

from __future__ import annotations

RETRY_DELAYS_SECONDS = (2, 4, 8, 16, 30, 60)


class TelemetryRetryTimer:
    def __init__(self):
        self.sequence: int | None = None
        self.attempts = 0
        self.due_at = 0.0

    def due(self, pending: dict[int, bytes], now: float) -> bool:
        oldest = next(iter(pending), None)
        if oldest is None:
            self.sequence = None
            self.attempts = 0
            return False
        if oldest != self.sequence:
            self.sequence = oldest
            self.attempts = 0
            self.due_at = now + RETRY_DELAYS_SECONDS[0]
            return False
        if now < self.due_at:
            return False
        self.attempts += 1
        delay = RETRY_DELAYS_SECONDS[min(self.attempts, len(RETRY_DELAYS_SECONDS) - 1)]
        self.due_at = now + delay
        return True
