"""Tests for rate_limiter module."""

import threading
import time

from bibtools.rate_limiter import RateLimiter, get_rate_limiter


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_first_execute_no_wait(self):
        """First execute should not wait."""
        limiter = RateLimiter(min_interval=1.0)
        start = time.monotonic()
        limiter.execute(lambda: None)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # Should be nearly instant

    def test_second_execute_waits(self):
        """Second execute should wait for min_interval."""
        limiter = RateLimiter(min_interval=0.2)
        limiter.execute(lambda: None)
        start = time.monotonic()
        limiter.execute(lambda: None)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.15  # Should wait ~0.2s (with some tolerance)
        assert elapsed < 0.4

    def test_no_wait_after_interval(self):
        """Should not wait if enough time has passed."""
        limiter = RateLimiter(min_interval=0.1)
        limiter.execute(lambda: None)
        time.sleep(0.15)  # Wait longer than interval
        start = time.monotonic()
        limiter.execute(lambda: None)
        elapsed = time.monotonic() - start
        assert elapsed < 0.05  # Should be nearly instant

    def test_execute_returns_result(self):
        """Execute should return function result."""
        limiter = RateLimiter(min_interval=0.0)
        result = limiter.execute(lambda: 42)
        assert result == 42

    def test_execute_with_rate_limiting(self):
        """Execute should apply rate limiting."""
        limiter = RateLimiter(min_interval=0.2)
        limiter.execute(lambda: None)
        start = time.monotonic()
        limiter.execute(lambda: None)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.15

    def test_reset(self):
        """Reset should clear the last request time."""
        limiter = RateLimiter(min_interval=0.2)
        limiter.execute(lambda: None)  # This marks completion
        limiter.reset()
        start = time.monotonic()
        limiter.execute(lambda: None)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # Should be nearly instant after reset

    def test_thread_safety(self):
        """Rate limiter should be thread-safe with execute."""
        limiter = RateLimiter(min_interval=0.1)
        results = []

        def worker():
            limiter.execute(lambda: results.append(1))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        start = time.monotonic()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.monotonic() - start

        assert len(results) == 5
        # 5 calls with 0.1s interval should take at least 0.4s (4 waits)
        assert total_time >= 0.35


class TestGetRateLimiter:
    """Tests for get_rate_limiter function."""

    def test_returns_same_instance_for_same_name(self):
        """Should return same limiter for same name."""
        limiter1 = get_rate_limiter("test_api_1", 1.0)
        limiter2 = get_rate_limiter("test_api_1", 1.0)
        assert limiter1 is limiter2

    def test_returns_different_instance_for_different_name(self):
        """Should return different limiter for different name."""
        limiter1 = get_rate_limiter("test_api_a", 1.0)
        limiter2 = get_rate_limiter("test_api_b", 1.0)
        assert limiter1 is not limiter2

    def test_uses_specified_interval(self):
        """Should use the specified interval."""
        limiter = get_rate_limiter("custom_api", 2.5)
        assert limiter.min_interval == 2.5
