import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_analyze_pr_post(monkeypatch):
    # Mock Celery task
    def mock_apply_async(args, kwargs=None):
        class Result:
            id = "test-task-id"
        return Result()

    from app.tasks import analyzer
    monkeypatch.setattr(analyzer.analyze_pull_request, "apply_async", mock_apply_async)

    response = client.post("/api/analyze-pr", json={
        "repo_url": "https://github.com/psf/requests",
        "pr_number": 7007
    })

    assert response.status_code == 200
    assert "task_id" in response.json()

def test_get_status_pending():
    response = client.get("/status/test-task-id")
    assert response.status_code in [200, 404]  # depending on Redis presence

def test_get_results_not_found():
    response = client.get("/results/nonexistent-id")
    assert response.status_code == 404
