"""Tests for WebSocket manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.websocket_manager import (
    WebSocketManager,
    WebSocketMessage,
)


@pytest.fixture
def ws_manager():
    """Create a WebSocket manager instance."""
    return WebSocketManager()


class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_message_creation(self):
        """Test creating a WebSocketMessage."""
        message = WebSocketMessage(
            type="test",
            data={"key": "value"},
        )

        assert message.type == "test"
        assert message.data == {"key": "value"}
        assert message.timestamp is not None  # Auto-generated

    def test_message_to_json(self):
        """Test converting message to JSON."""
        message = WebSocketMessage(
            type="test",
            data={"key": "value"},
        )

        json_str = message.to_json()

        assert isinstance(json_str, str)
        assert '"type": "test"' in json_str
        assert '"data": {"key": "value"}' in json_str
        assert '"timestamp"' in json_str


class TestWebSocketManager:
    """Tests for WebSocketManager class."""

    @pytest.mark.asyncio
    async def test_connect(self, ws_manager):
        """Test connecting a WebSocket."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        await ws_manager.connect(mock_websocket, "test_channel")

        # Verify accept was called
        mock_websocket.accept.assert_called_once()

        # Verify connection was added to channel
        assert mock_websocket in ws_manager.connections["test_channel"]
        assert "test_channel" in ws_manager.connection_channels[mock_websocket]

        # Verify welcome message was sent
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, ws_manager):
        """Test disconnecting a WebSocket."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        await ws_manager.connect(mock_websocket, "test_channel")
        assert mock_websocket in ws_manager.connections["test_channel"]

        ws_manager.disconnect(mock_websocket)

        # Verify connection was removed
        assert mock_websocket not in ws_manager.connections["test_channel"]
        assert mock_websocket not in ws_manager.connection_channels

    @pytest.mark.asyncio
    async def test_send_personal_message(self, ws_manager):
        """Test sending a personal message."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        message = WebSocketMessage(
            type="personal",
            data={"message": "Hello"},
        )

        await ws_manager.send_personal_message(mock_websocket, message)

        mock_websocket.send_text.assert_called_once()
        sent_json = mock_websocket.send_text.call_args[0][0]
        assert '"type": "personal"' in sent_json

    @pytest.mark.asyncio
    async def test_broadcast(self, ws_manager):
        """Test broadcasting to a channel."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws1.send_text = AsyncMock()
        mock_ws2.send_text = AsyncMock()

        await ws_manager.connect(mock_ws1, "test_channel")
        await ws_manager.connect(mock_ws2, "test_channel")

        message = WebSocketMessage(
            type="broadcast",
            data={"message": "Hello all"},
        )

        await ws_manager.broadcast("test_channel", message)

        # Both connections should receive the message
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_with_disconnected_client(self, ws_manager):
        """Test broadcasting handles disconnected clients gracefully."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws1.send_text = AsyncMock()
        mock_ws2.send_text = AsyncMock(side_effect=Exception("Connection closed"))

        await ws_manager.connect(mock_ws1, "test_channel")
        await ws_manager.connect(mock_ws2, "test_channel")

        message = WebSocketMessage(
            type="broadcast",
            data={"message": "Hello"},
        )

        await ws_manager.broadcast("test_channel", message)

        # ws1 should receive the message
        mock_ws1.send_text.assert_called_once()

        # ws2 should be disconnected after error
        assert mock_ws2 not in ws_manager.connections["test_channel"]

    @pytest.mark.asyncio
    async def test_broadcast_agent_status(self, ws_manager):
        """Test broadcasting agent status."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        await ws_manager.connect(mock_websocket, "agents")

        await ws_manager.broadcast_agent_status("agent-123", "running", {"job_id": "job-456"})

        mock_websocket.send_text.assert_called_once()
        sent_json = mock_websocket.send_text.call_args[0][0]
        assert '"type": "agent_status"' in sent_json
        assert '"agent_id": "agent-123"' in sent_json
        assert '"status": "running"' in sent_json

    @pytest.mark.asyncio
    async def test_broadcast_job_update(self, ws_manager):
        """Test broadcasting job update."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        await ws_manager.connect(mock_websocket, "jobs")

        await ws_manager.broadcast_job_update("job-123", "completed", {"result": "success"})

        mock_websocket.send_text.assert_called_once()
        sent_json = mock_websocket.send_text.call_args[0][0]
        assert '"type": "job_update"' in sent_json
        assert '"job_id": "job-123"' in sent_json
        assert '"status": "completed"' in sent_json

    @pytest.mark.asyncio
    async def test_broadcast_opportunity_found(self, ws_manager):
        """Test broadcasting opportunity discovery."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        await ws_manager.connect(mock_websocket, "opportunities")

        opportunity = {"title": "Test Opportunity", "url": "https://example.com"}
        await ws_manager.broadcast_opportunity_found(opportunity)

        mock_websocket.send_text.assert_called_once()
        sent_json = mock_websocket.send_text.call_args[0][0]
        assert '"type": "opportunity_found"' in sent_json

    @pytest.mark.asyncio
    async def test_broadcast_verification_complete(self, ws_manager):
        """Test broadcasting verification completion."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        await ws_manager.connect(mock_websocket, "verifications")

        verification = {"opportunity_id": "123", "status": "verified"}
        await ws_manager.broadcast_verification_complete(verification)

        mock_websocket.send_text.assert_called_once()
        sent_json = mock_websocket.send_text.call_args[0][0]
        assert '"type": "verification_complete"' in sent_json

    @pytest.mark.asyncio
    async def test_broadcast_alert(self, ws_manager):
        """Test broadcasting alert."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        await ws_manager.connect(mock_websocket, "alerts")

        alert = {"title": "Test Alert", "severity": "high"}
        await ws_manager.broadcast_alert(alert)

        mock_websocket.send_text.assert_called_once()
        sent_json = mock_websocket.send_text.call_args[0][0]
        assert '"type": "alert"' in sent_json

    @pytest.mark.asyncio
    async def test_broadcast_metrics(self, ws_manager):
        """Test broadcasting metrics."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        await ws_manager.connect(mock_websocket, "metrics")

        metrics = {"active_agents": 5, "jobs_completed": 100}
        await ws_manager.broadcast_metrics(metrics)

        mock_websocket.send_text.assert_called_once()
        sent_json = mock_websocket.send_text.call_args[0][0]
        assert '"type": "metrics"' in sent_json

    def test_get_connection_count_channel(self, ws_manager):
        """Test getting connection count for a specific channel."""
        mock_ws1 = MagicMock()
        mock_ws2 = MagicMock()
        mock_ws3 = MagicMock()

        ws_manager.connections["test_channel"] = [mock_ws1, mock_ws2]
        ws_manager.connections["other_channel"] = [mock_ws3]

        count = ws_manager.get_connection_count("test_channel")
        assert count == 2

        count = ws_manager.get_connection_count("other_channel")
        assert count == 1

    def test_get_connection_count_all(self, ws_manager):
        """Test getting total connection count."""
        mock_ws1 = MagicMock()
        mock_ws2 = MagicMock()
        mock_ws3 = MagicMock()

        ws_manager.connections["test_channel"] = [mock_ws1, mock_ws2]
        ws_manager.connections["other_channel"] = [mock_ws3]

        count = ws_manager.get_connection_count()
        assert count == 3

    def test_get_connection_count_empty(self, ws_manager):
        """Test connection count when no connections."""
        count = ws_manager.get_connection_count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_multiple_channels_same_connection(self, ws_manager):
        """Test a connection can be in multiple channels."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        await ws_manager.connect(mock_websocket, "channel1")
        await ws_manager.connect(mock_websocket, "channel2")

        assert mock_websocket in ws_manager.connections["channel1"]
        assert mock_websocket in ws_manager.connections["channel2"]
        assert len(ws_manager.connection_channels[mock_websocket]) == 2

        # Disconnect should remove from all channels
        ws_manager.disconnect(mock_websocket)
        assert mock_websocket not in ws_manager.connections["channel1"]
        assert mock_websocket not in ws_manager.connections["channel2"]
