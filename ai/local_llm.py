"""
Local LLM Integration Module for cliagent / Autobot.
Connects to Ollama or LM Studio via OpenAI-compatible API endpoints.
Provides automatic model discovery, local model querying, and intent parsing.
"""
import json
import httpx
from typing import Dict, Any, Optional, List

from config import LOCAL_LLM_URL, LOCAL_LLM_MODEL
from ai.base import SYSTEM_PROMPT, sanitize_json_response


class LocalLLMClient:
    """
    Client for interacting with local Ollama / LM Studio endpoints.
    """

    def __init__(self, base_url: str = LOCAL_LLM_URL, model_name: Optional[str] = None):
        # Normalize base_url to point to /chat/completions endpoint
        self.base_url = base_url.rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"
        self.endpoint = f"{self.base_url}/chat/completions"
        self._model_name = model_name or LOCAL_LLM_MODEL or ""

    @property
    def model_name(self) -> str:
        return self._model_name

    def set_model(self, model_name: str) -> None:
        """Sets active local model name."""
        self._model_name = model_name

    def list_installed_models(self) -> List[str]:
        """
        Queries local Ollama/LM Studio server and returns a list of installed model names.
        """
        try:
            models_url = f"{self.base_url}/models"
            with httpx.Client(timeout=2.0) as client:
                res = client.get(models_url)
                if res.status_code == 200:
                    data = res.json()
                    models_list = data.get("data", [])
                    return [m.get("id") for m in models_list if m.get("id")]
        except Exception:
            return []
        return []

    def resolve_model_name(self) -> str:
        """
        Resolves the best available local model name:
        1. If explicitly configured model exists in installed list, returns it.
        2. If substring matches an installed model (e.g. 'qwen' -> 'qwen3.5:4b'), returns match.
        3. If not configured or not matched, falls back to first installed model.
        4. If no models installed, returns default model name.
        """
        installed = self.list_installed_models()
        if not installed:
            return self._model_name or "gemma2:4b"

        if self._model_name:
            # Check exact match
            for m in installed:
                if m.lower() == self._model_name.lower():
                    return m
            # Check substring match
            for m in installed:
                if self._model_name.lower() in m.lower():
                    return m

        # Fallback to first available installed model
        return installed[0]

    def is_available(self) -> bool:
        """
        Checks if the local LLM server (Ollama/LM Studio) is reachable
        and has at least one model installed.
        """
        installed = self.list_installed_models()
        return len(installed) > 0

    def parse_intent(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Sends user prompt to local LLM and returns parsed JSON intent object.
        """
        target_model = self.resolve_model_name()
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,  # Low temperature for strict structured output
            "response_format": {"type": "json_object"},  # Standard JSON mode request
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(self.endpoint, json=payload)
                if response.status_code != 200:
                    return None

                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]
                clean_json_str = sanitize_json_response(raw_content)
                return json.loads(clean_json_str)
        except Exception:
            return None
