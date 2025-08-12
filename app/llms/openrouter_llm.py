import requests
from crewai import BaseLLM
import logging

logger = logging.getLogger(__name__)

class OpenRouterLLM(BaseLLM):
    def __init__(self, model: str, api_key: str, endpoint: str = "https://openrouter.ai/api/v1/chat/completions", temperature: float = 0.0):
        super().__init__(model=model, temperature=temperature)
        self.api_key = api_key
        self.endpoint = endpoint

    def call(self, messages, tools=None, callbacks=None, available_functions=None):
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }

        logger.info(f"🎯 OpenRouter request payload: {payload}")
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )

        logger.info(f"🧪 OpenRouter response status: {response.status_code}, body: {response.text}")

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]
