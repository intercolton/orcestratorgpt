"""LLM call wrapper for role-specific prompts."""
from typing import Any, Dict

from orchestrator.prompts import ROLE_PROMPTS
from orchestrator.util import logger, safe_json


def call(role: str, input_json: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate an LLM call; in production replace with OpenAI call."""
    prompt = ROLE_PROMPTS.get(role, "")
    logger.info("LLM call role=%s prompt=%s input=%s", role, prompt[:60], safe_json(input_json))
    # Placeholder deterministic response for demo purposes
    return {"role": role, "received": input_json, "prompt": prompt}
