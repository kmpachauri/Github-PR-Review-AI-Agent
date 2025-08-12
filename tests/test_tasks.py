import pytest
from app.tasks.analyzer import analyze_pull_request

def test_analyze_pull_request_with_invalid_repo(monkeypatch):
    result = analyze_pull_request.run("https://github.com/psf/requests", 7007, None)
    assert result is None 
