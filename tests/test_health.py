"""Health check endpoint tests"""

import pytest
from fastapi.testclient import TestClient

from src.server import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    """Test that the health endpoint returns 200"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
