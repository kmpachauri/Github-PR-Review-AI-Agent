from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_analyze_pr():
    response = client.post("/api/analyze-pr", json={
        "repo_url": "https://github.com/user/repo",
        "pr_number": 123
    })
    assert response.status_code == 200
    assert "task_id" in response.json()
