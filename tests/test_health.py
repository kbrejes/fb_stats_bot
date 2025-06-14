"""
Tests for health check functionality.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.utils.health_check import HealthChecker


class TestHealthChecker:
    """Test health check functionality."""

    @pytest.fixture
    def health_checker(self):
        """Create health checker instance."""
        return HealthChecker()

    @pytest.mark.asyncio
    async def test_get_system_metrics(self, health_checker):
        """Test system metrics collection."""
        metrics = health_checker.get_system_metrics()

        assert "cpu" in metrics
        assert "memory" in metrics
        assert "disk" in metrics
        assert "uptime_seconds" in metrics
        assert "uptime_human" in metrics

        # Check data types
        assert isinstance(metrics["cpu"]["usage_percent"], (int, float))
        assert isinstance(metrics["memory"]["usage_percent"], (int, float))
        assert isinstance(metrics["disk"]["usage_percent"], (int, float))

    def test_format_uptime(self, health_checker):
        """Test uptime formatting."""
        # Test different time periods
        assert "5m" in health_checker._format_uptime(300)  # 5 minutes
        assert "1h 5m" in health_checker._format_uptime(3900)  # 1 hour 5 minutes
        assert "1d 1h 5m" in health_checker._format_uptime(
            90300
        )  # 1 day 1 hour 5 minutes

    @pytest.mark.asyncio
    @patch("src.utils.health_check.get_session")
    async def test_check_database_success(self, mock_get_session, health_checker):
        """Test successful database check."""
        # Mock successful database connection
        mock_session = AsyncMock()
        mock_session.execute.return_value = None
        mock_get_session.return_value = mock_session

        result = await health_checker.check_database()

        assert result["status"] == "healthy"
        assert "Database connection successful" in result["message"]

    @pytest.mark.asyncio
    @patch("src.utils.health_check.get_session")
    async def test_check_database_failure(self, mock_get_session, health_checker):
        """Test database check failure."""
        # Mock database connection failure
        mock_get_session.side_effect = Exception("Connection failed")

        result = await health_checker.check_database()

        assert result["status"] == "unhealthy"
        assert "Database error" in result["message"]

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_check_openai_api_success(self, mock_get, health_checker):
        """Test successful OpenAI API check."""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response

        result = await health_checker.check_openai_api()

        assert result["status"] == "healthy"
        assert "OpenAI API accessible" in result["message"]
        assert "response_time_ms" in result

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_check_facebook_api_success(self, mock_get, health_checker):
        """Test successful Facebook API check."""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response

        result = await health_checker.check_facebook_api()

        assert result["status"] == "healthy"
        assert "Facebook API accessible" in result["message"]
        assert "response_time_ms" in result

    @pytest.mark.asyncio
    async def test_get_full_health_status(self, health_checker):
        """Test full health status check."""
        with patch.object(health_checker, "check_database") as mock_db, patch.object(
            health_checker, "check_openai_api"
        ) as mock_openai, patch.object(health_checker, "check_facebook_api") as mock_fb:

            # Mock all checks as healthy
            mock_db.return_value = {"status": "healthy", "message": "OK"}
            mock_openai.return_value = {"status": "healthy", "message": "OK"}
            mock_fb.return_value = {"status": "healthy", "message": "OK"}

            result = await health_checker.get_full_health_status()

            assert result["status"] == "healthy"
            assert "services" in result
            assert "database" in result["services"]
            assert "openai_api" in result["services"]
            assert "facebook_api" in result["services"]
            assert "system" in result
            assert "timestamp" in result
            assert "environment" in result

    @pytest.mark.asyncio
    async def test_get_full_health_status_unhealthy(self, health_checker):
        """Test full health status when some services are unhealthy."""
        with patch.object(health_checker, "check_database") as mock_db, patch.object(
            health_checker, "check_openai_api"
        ) as mock_openai, patch.object(health_checker, "check_facebook_api") as mock_fb:

            # Mock one check as unhealthy
            mock_db.return_value = {"status": "unhealthy", "message": "Error"}
            mock_openai.return_value = {"status": "healthy", "message": "OK"}
            mock_fb.return_value = {"status": "healthy", "message": "OK"}

            result = await health_checker.get_full_health_status()

            assert result["status"] == "unhealthy"
