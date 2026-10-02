"""
Cloud LLM Integration Module for cliagent / Autobot.
Provides fallback / primary cloud LLM connection via universal OpenAI-compatible endpoints
(OpenAI, Groq, OpenRouter, DeepSeek, Mistral, Together, etc.).
"""
import json
import httpx
from typing import Dict, Any, Optional

import config
from ai.base import SYSTEM_PROMPT, sanitize_json_response


class CloudLLMClient:
    """
    Client for interacting with Cloud LLMs using OpenAI-compatible chat completion APIs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._model_name = model_name

    @property
    def api_key(self) -> str:
        if self._api_key is not None and self._api_key != "":
            return self._api_key
        # Check latest config / persisted settings
        cfg = config.load_user_config()
        return config.LLM_API_KEY or cfg.get("llm_api_key", "")

    @property
    def base_url(self) -> str:
        if self._base_url is not None:
            return self._base_url
        cfg = config.load_user_config()
        return config.LLM_BASE_URL or cfg.get("llm_base_url", "https://api.openai.com/v1")

    @property
    def model_name(self) -> str:
        if self._model_name is not None:
            return self._model_name
        cfg = config.load_user_config()
        return config.LLM_MODEL or cfg.get("llm_model", "gpt-4o-mini")

    def set_api_key(self, api_key: str) -> None:
        """Dynamically updates the API key for the current session."""
        self._api_key = api_key

    def set_model(self, model_name: str) -> None:
        """Dynamically updates the model name."""
        self._model_name = model_name

    @property
    def endpoint(self) -> str:
        url = self.base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            if not url.endswith("/v1"):
                url = f"{url}/v1"
            url = f"{url}/chat/completions"
        return url

    def is_available(self) -> bool:
        """Checks if a valid API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    def parse_intent(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Sends user prompt to Cloud LLM and returns parsed JSON intent object.
        """
        if not self.is_available():
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(self.endpoint, headers=headers, json=payload)
                if response.status_code != 200:
                    return None

                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]
                clean_json_str = sanitize_json_response(raw_content)
                return json.loads(clean_json_str)
        except Exception:
            return None
