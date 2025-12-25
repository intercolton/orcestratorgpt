"""Utility helpers for logging and formatting."""
import json
import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("wms-orchestrator")


def safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)
