"""
Base AI Interface and System Prompts for cliagent.
Defines structured JSON schemas and system prompts for LLM intent parsing.
"""
import re
from typing import Dict, Any, Optional

SYSTEM_PROMPT = """You are an AI File System Intent Parser for Autobot.
Your sole job is to translate a user's natural language request into a single structured JSON object.

You MUST respond ONLY with valid JSON. Do not include markdown block formatting, extra text, or explanations outside the JSON.

JSON Schema format:
{
  "action": "locate" | "rename" | "move",
  "query": "<search query or filename pattern>",
  "source_dir": "<start search directory, default '.'>",
  "target_dir": "<destination folder path for move actions, or null>",
  "new_name": "<new filename, replacement pattern, or prefix/suffix for rename actions, or null>",
  "filters": {
    "extensions": ["<extension1>", "<extension2>"],
    "min_size_mb": <number or null>,
    "max_size_mb": <number or null>,
    "search_type": "files" | "folders" | "all"
  }
}

Rules:
1. 'action' must be strictly one of: 'locate', 'rename', 'move'.
2. If the user specifies an extension (e.g. '.pdf', 'png'), put it in filters.extensions as a list of strings without leading dots.
3. If no target directory is specified for move, set 'target_dir' to null.
4. Default 'source_dir' is '.' unless a specific folder like 'Desktop' or 'Downloads' is mentioned.
"""

def sanitize_json_response(raw_text: str) -> str:
    """
    Strips markdown code blocks, extracts JSON between ```json ... ``` or
    finds the outermost JSON object { ... } from LLM output.
    """
    text = raw_text.strip()
    
    # 1. Check for markdown code fences anywhere in text
    fence_pattern = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_pattern:
        candidate = fence_pattern.group(1).strip()
        if candidate.startswith("{") or candidate.startswith("["):
            return candidate

    # 2. If text starts with ``` but wasn't caught by regex
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 3. If direct text is a valid JSON boundary, return it
    if text.startswith("{") and text.endswith("}"):
        return text

    # 4. Search for the outermost balanced { ... } object in the text
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1].strip()

    return text
