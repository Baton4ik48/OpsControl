import pytest
from app.services.login_throttle import LoginThrottle, TooManyAttempts


class TestLoginThrottle:

    @pytest.fixture
    def throttle(self):
        return LoginThrottle(max_attempts=3, block_seconds=10)

    # ============================================
    # CHECK
    # ============================================

    def test_check_first_attempt_ok(self, throttle):
        throttle.check("user")  # не падает

    def test_check_within_limit_ok(self, throttle, monkeypatch):
        t = 1000
        monkeypatch.setattr("time.time", lambda: t)

        # ДО лимита
        for _ in range(throttle.max_attempts - 1):
            throttle.register_fail("user")

        throttle.check("user")  # OK

    def test_check_exactly_at_limit_blocks(self, throttle, monkeypatch):
        t = 1000
        monkeypatch.setattr("time.time", lambda: t)

        # РОВНО лимит
        for _ in range(throttle.max_attempts):
            throttle.register_fail("user")

        with pytest.raises(TooManyAttempts):
            throttle.check("user")

    def test_check_unblocked_after_time(self, throttle, monkeypatch):
        t = 1000
        monkeypatch.setattr("time.time", lambda: t)

        for _ in range(throttle.max_attempts):
            throttle.register_fail("user")

        # прошло больше block_seconds
        monkeypatch.setattr("time.time", lambda: t + 11)

        throttle.check("user")  # OK

        # старые попытки должны очиститься
        assert throttle.failed["user"] == []

    # ============================================
    # REGISTER_FAIL
    # ============================================

    def test_register_fail_accumulates(self, throttle, monkeypatch):
        monkeypatch.setattr("time.time", lambda: 1000)

        throttle.register_fail("user")

        assert "user" in throttle.failed
        assert len(throttle.failed["user"]) == 1

    # ============================================
    # RESET
    # ============================================

    def test_reset_clears_key(self, throttle, monkeypatch):
        monkeypatch.setattr("time.time", lambda: 1000)

        for _ in range(throttle.max_attempts):
            throttle.register_fail("user")

        throttle.reset("user")

        throttle.check("user")  # не падает

        assert throttle.failed["user"] == []

    def test_reset_nonexistent_key(self, throttle):
        throttle.reset("unknown")  # не падает

    # ============================================
    # TIME UNTIL UNBLOCK
    # ============================================

    def test_time_until_unblock_not_blocked(self, throttle):
        assert throttle.time_until_unblock("user") == 0

    def test_time_until_unblock_blocked(self, throttle, monkeypatch):
        t = 1000
        monkeypatch.setattr("time.time", lambda: t)

        for _ in range(throttle.max_attempts):
            throttle.register_fail("user")

        remaining = throttle.time_until_unblock("user")

        assert remaining > 0
        assert remaining <= throttle.block_seconds

    def test_time_until_unblock_after_expired(self, throttle, monkeypatch):
        t = 1000
        monkeypatch.setattr("time.time", lambda: t)

        for _ in range(throttle.max_attempts):
            throttle.register_fail("user")

        monkeypatch.setattr("time.time", lambda: t + 20)

        assert throttle.time_until_unblock("user") == 0
