"""
Unified AI Intent Parser Router for cliagent / Autobot.
Automatically routes requests between Local LLMs (Ollama/LM Studio) and Cloud LLMs (OpenAI, Groq, OpenRouter, etc.).
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

    def set_cloud_api_key(self, api_key: str) -> None:
        """Sets the cloud API key for dynamic configuration."""
        self.cloud_client.set_api_key(api_key)

    def parse(self, user_prompt: str, preferred_model: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Parses natural language user_prompt into a structured JSON action payload.

        :param user_prompt: Plain English command (e.g. "Move all PNG files from Desktop to Pictures")
        :param preferred_model: Session active model preference (e.g. "Local LLM (qwen3.5:4b)")
        :return: Tuple of (parsed_json_dict, provider_or_error_message)
        """
        # If user explicitly selected a local model in REPL (e.g. "Local LLM (qwen3.5:4b)")
        if preferred_model and "Local" in preferred_model:
            if "(" in preferred_model and ")" in preferred_model:
                sub_model = preferred_model.split("(")[1].split(")")[0].strip()
                if sub_model and sub_model != "Local":
                    self.local_client.set_model(sub_model)

        # Determine attempt order based on user's active session choice
        prefer_cloud = bool(preferred_model and "Cloud" in preferred_model)

        errors = []

        if prefer_cloud:
            # 1. Try Cloud LLM first
            if self.cloud_client.is_available():
                result = self.cloud_client.parse_intent(user_prompt)
                if result:
                    return result, f"Cloud LLM ({self.cloud_client.model_name})"
                if self.cloud_client.last_error:
                    errors.append(self.cloud_client.last_error)

            # Fallback to Local LLM if available
            if self.local_client.is_available():
                result = self.local_client.parse_intent(user_prompt)
                if result:
                    return result, f"Local LLM ({self.local_client.resolve_model_name()})"
                if self.local_client.last_error:
                    errors.append(self.local_client.last_error)
        else:
            # 1. Try Local LLM first (Ollama / LM Studio)
            if self.local_client.is_available():
                result = self.local_client.parse_intent(user_prompt)
                if result:
                    return result, f"Local LLM ({self.local_client.resolve_model_name()})"
                if self.local_client.last_error:
                    errors.append(self.local_client.last_error)

            # Fallback to Cloud LLM API if available
            if self.cloud_client.is_available():
                result = self.cloud_client.parse_intent(user_prompt)
                if result:
                    return result, f"Cloud LLM ({self.cloud_client.model_name})"
                if self.cloud_client.last_error:
                    errors.append(self.cloud_client.last_error)

        # If both failed or unavailable, report detailed diagnostics
        if errors:
            return None, " | ".join(errors)

        if not self.local_client.is_available() and not self.cloud_client.is_available():
            return None, "No local models found in Ollama and no Cloud LLM API key configured."

        return None, "AI request failed to generate a valid intent response."
