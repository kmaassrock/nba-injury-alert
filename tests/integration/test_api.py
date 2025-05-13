"""
Integration tests for the API endpoints.
"""
import pytest
from fastapi import status


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}


def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.json()


def test_api_docs(client):
    """Test that the API documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == status.HTTP_200_OK
    assert "swagger" in response.text.lower()


def test_redoc(client):
    """Test that the ReDoc documentation is accessible."""
    response = client.get("/redoc")
    assert response.status_code == status.HTTP_200_OK
    assert "redoc" in response.text.lower()


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/players",
        "/api/players/top100",
        "/api/players/teams",
        "/api/injuries/reports",
        "/api/injuries/changes",
    ],
)
def test_api_endpoints_exist(client, endpoint):
    """Test that the API endpoints exist."""
    response = client.get(endpoint)
    # We don't care about the response code here, just that the endpoint exists
    # It might return 401 if authentication is required, or 404 if no data exists
    assert response.status_code != status.HTTP_404_NOT_FOUND
