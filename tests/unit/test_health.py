"""Tests for the /health route's safety event count."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
import redis
from fastapi import HTTPException

from api.routes.health import health_check


async def _call_health_check(db):
    """Call the route and return its body, whether it answers 200 or 503."""
    try:
        return await health_check(db=db)
    except HTTPException as exc:
        return exc.detail


@pytest.mark.unit
class TestHealthSafetyEvents:
    """Test suite for safety_events_last_hour in health_check."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock async database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_redis(self):
        """Patch redis.Redis.from_url to return a mock client."""
        client = Mock()
        with patch.object(redis.Redis, "from_url", return_value=client):
            yield client

    @pytest.mark.asyncio
    async def test_sums_counters_across_event_types(self, mock_db_session, mock_redis):
        """Test the field is the sum of every event type's counter."""
        counters = {
            "safety:events:injection_attempt": "2",
            "safety:events:pii_detected": "1",
        }
        mock_redis.get = Mock(side_effect=counters.get)

        body = await _call_health_check(mock_db_session)

        assert body["safety_events_last_hour"] == 3

    @pytest.mark.asyncio
    async def test_missing_counters_give_zero(self, mock_db_session, mock_redis):
        """Test the field is 0 when no counters exist."""
        mock_redis.get = Mock(return_value=None)

        body = await _call_health_check(mock_db_session)

        assert body["safety_events_last_hour"] == 0

    @pytest.mark.asyncio
    async def test_redis_connection_error_gives_zero(self, mock_db_session, mock_redis):
        """Test a Redis failure leaves the field at 0 and the route still responds."""
        mock_redis.get = Mock(side_effect=redis.ConnectionError("connection refused"))

        body = await _call_health_check(mock_db_session)

        assert body["safety_events_last_hour"] == 0
