from unittest.mock import patch

from app.core.rag.qdrant_client import create_qdrant_client


@patch("app.core.rag.qdrant_client.QdrantClient")
def test_create_qdrant_client_local_without_api_key(mock_client_cls):
    create_qdrant_client(host="localhost", port=6333)

    mock_client_cls.assert_called_once_with(host="localhost", port=6333)


@patch("app.core.rag.qdrant_client.QdrantClient")
def test_create_qdrant_client_cloud_with_api_key(mock_client_cls):
    create_qdrant_client(
        host="cluster.sa-east-1-0.aws.cloud.qdrant.io",
        port=6333,
        api_key="test-key",
    )

    mock_client_cls.assert_called_once_with(
        host="cluster.sa-east-1-0.aws.cloud.qdrant.io",
        port=6333,
        https=True,
        api_key="test-key",
    )
