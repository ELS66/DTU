import unittest

from retry_policy import TelemetryRetryTimer


class RetryPolicyTest(unittest.TestCase):
    def test_oldest_frame_retries_with_backoff_and_resets_on_ack(self):
        timer = TelemetryRetryTimer()
        pending = {1: b"first", 2: b"second"}
        self.assertFalse(timer.due(pending, 0))
        self.assertFalse(timer.due(pending, 1.99))
        self.assertTrue(timer.due(pending, 2))
        self.assertFalse(timer.due(pending, 5.99))
        self.assertTrue(timer.due(pending, 6))
        del pending[1]
        self.assertFalse(timer.due(pending, 6))
        self.assertTrue(timer.due(pending, 8))
        pending.clear()
        self.assertFalse(timer.due(pending, 8))
        self.assertIsNone(timer.sequence)

    def test_delay_caps_at_sixty_seconds(self):
        timer = TelemetryRetryTimer()
        pending = {1: b"frame"}
        self.assertFalse(timer.due(pending, 0))
        now = 0
        for delay in (2, 4, 8, 16, 30, 60, 60):
            now += delay
            self.assertTrue(timer.due(pending, now))
            self.assertFalse(timer.due(pending, now))


if __name__ == "__main__":
    unittest.main()
