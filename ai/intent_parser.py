"""
Unified AI Intent Parser Router for cliagent.
Automatically routes requests between Local Gemma/Qwen (Ollama/LM Studio) and Cloud Gemini APIs.
"""
from typing import Dict, Any, Tuple, Optional
from ai.local_llm import LocalLLMClient
from ai.cloud_llm import CloudLLMClient


class AIIntentParser:
    """
    Main entry point for AI natural language parsing.
    """

    def __init__(self):
        self.local_client = LocalLLMClient()
        self.cloud_client = CloudLLMClient()

    def parse(self, user_prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Parses natural language user_prompt into a structured JSON action payload.

        :param user_prompt: Plain English command (e.g. "Move all PNG files from Desktop to Pictures")
        :return: Tuple of (parsed_json_dict, provider_name)
        """
        # 1. Try Local LLM (Ollama / LM Studio with Gemma 4B / Qwen 4B)
        if self.local_client.is_available():
            result = self.local_client.parse_intent(user_prompt)
            if result:
                return result, f"Local LLM ({self.local_client.model_name})"

        # 2. Fall back to Cloud Gemini API if available
        if self.cloud_client.is_available():
            result = self.cloud_client.parse_intent(user_prompt)
            if result:
                return result, "Cloud Gemini API"

        return None, "None (No AI provider available or request failed)"
