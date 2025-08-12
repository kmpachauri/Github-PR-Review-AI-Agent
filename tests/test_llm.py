import pytest
from app.llms.openrouter_llm import OpenRouterLLM

def test_openrouter_llm_call(monkeypatch):
    def mock_post(*args, **kwargs):
        class Response:
            def raise_for_status(self): pass
            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"files": [], "summary": {"total_files": 0, "total_issues": 0, "critical_issues": 0}}'
                            }
                        }
                    ]
                }
            status_code = 200
            text = '{"mocked": "true"}'
        return Response()

    import requests
    monkeypatch.setattr(requests, "post", mock_post)

    client = OpenRouterLLM(api_key="test", model="openai/gpt-4o")
    result = client.call("Test message")
    assert "files" in result
