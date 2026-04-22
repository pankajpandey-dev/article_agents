import json
import re


def safe_parse(text: str):
    """Parse model JSON; tolerate markdown fences and leading/trailing noise."""
    if not text or not str(text).strip():
        return None
    raw = str(text).strip()

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if fence:
        raw = fence.group(1).strip()

    raw = raw.lstrip("\ufeff")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None
