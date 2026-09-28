"""
Local LLM Integration Module for cliagent.
Connects to Ollama or LM Studio (Gemma 4B / Qwen 4B) via OpenAI-compatible API endpoints.
"""
import json
import httpx
from typing import Dict, Any, Optional

from config import LOCAL_LLM_URL, LOCAL_LLM_MODEL
from ai.base import SYSTEM_PROMPT, sanitize_json_response


class LocalLLMClient:
    """
    Client for interacting with local Ollama / LM Studio endpoints.
    """

    def __init__(self, base_url: str = LOCAL_LLM_URL, model_name: str = LOCAL_LLM_MODEL):
        # Normalize base_url to point to /chat/completions endpoint
        self.base_url = base_url.rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"
        self.endpoint = f"{self.base_url}/chat/completions"
        self.model_name = model_name

    def is_available(self) -> bool:
        """
        Checks if the local LLM server (Ollama/LM Studio) is reachable.
        """
        try:
            # Check models endpoint
            models_url = f"{self.base_url}/models"
            with httpx.Client(timeout=2.0) as client:
                res = client.get(models_url)
                return res.status_code == 200
        except Exception:
            return False

    def parse_intent(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Sends user prompt to local Gemma/Qwen LLM and returns parsed JSON intent object.
        """
        payload = {
            "model": self.model_name,
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
        except Exception as e:
            return None
