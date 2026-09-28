"""
Cloud Gemini LLM Integration Module for cliagent.
Provides fallback / primary cloud LLM connection via Gemini API.
"""
import json
import httpx
from typing import Dict, Any, Optional

from config import GEMINI_API_KEY
from ai.base import SYSTEM_PROMPT, sanitize_json_response


class CloudLLMClient:
    """
    Client for interacting with Cloud Gemini API.
    """

    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def parse_intent(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        if not self.is_available():
            return None

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\n\nUser Request: {user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.endpoint, json=payload)
                if response.status_code != 200:
                    return None

                data = response.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                clean_json_str = sanitize_json_response(raw_text)
                return json.loads(clean_json_str)
        except Exception:
            return None
