from typing import Any


def tiptap_to_text(value: Any) -> str:
    parts: list[str] = []
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            parts.append(value["text"])
        for child in value.get("content", []):
            parts.append(tiptap_to_text(child))
    elif isinstance(value, list):
        for child in value:
            parts.append(tiptap_to_text(child))
    return " ".join(part.strip() for part in parts if part.strip())
