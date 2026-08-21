from unittest.mock import MagicMock, patch

import pytest

from app.core.rag.qdrant_wait import wait_for_qdrant


@patch("app.core.rag.qdrant_wait.time.sleep")
@patch("app.core.rag.qdrant_wait.QdrantClient")
def test_wait_for_qdrant_succeeds_on_first_attempt(mock_client_cls, mock_sleep):
    mock_client_cls.return_value.get_collections.return_value = []

    wait_for_qdrant(host="localhost", port=6333, timeout_seconds=5.0)

    mock_client_cls.assert_called_once_with(host="localhost", port=6333)
    mock_sleep.assert_not_called()


@patch("app.core.rag.qdrant_wait.time.sleep")
@patch("app.core.rag.qdrant_wait.QdrantClient")
def test_wait_for_qdrant_retries_until_success(mock_client_cls, mock_sleep):
    mock_client = MagicMock()
    mock_client.get_collections.side_effect = [ConnectionError("down"), []]
    mock_client_cls.return_value = mock_client

    wait_for_qdrant(host="vector-db", port=6333, timeout_seconds=5.0)

    assert mock_client.get_collections.call_count == 2
    mock_sleep.assert_called_once()


@patch("app.core.rag.qdrant_wait.time.sleep")
@patch("app.core.rag.qdrant_wait.time.monotonic")
@patch("app.core.rag.qdrant_wait.QdrantClient")
def test_wait_for_qdrant_raises_after_timeout(
    mock_client_cls, mock_monotonic, mock_sleep
):
    mock_client_cls.return_value.get_collections.side_effect = ConnectionError("down")
    mock_monotonic.side_effect = [0.0, 0.0, 0.05, 0.2]

    with pytest.raises(RuntimeError, match="Qdrant not available at localhost:6333"):
        wait_for_qdrant(
            host="localhost",
            port=6333,
            interval_seconds=0.05,
            timeout_seconds=0.1,
        )
