import re


class GuardrailError(ValueError):
    """Raised when input or output fails guardrail checks."""


_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|system)\s+", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"new\s+instructions\s*:", re.I),
    re.compile(r"system\s*:\s*", re.I),
    re.compile(r"<\s*/?\s*system\s*>", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"developer\s+mode", re.I),
)


def sanitize_text(text: str, max_length: int = 8000) -> str:
    cleaned = text.replace("\x00", "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned) if len(cleaned) < 500 else cleaned
    if len(cleaned) > max_length:
        raise GuardrailError(f"Message exceeds maximum length of {max_length} characters.")
    if not cleaned:
        raise GuardrailError("Message cannot be empty.")
    return cleaned


def detect_prompt_injection(text: str) -> str | None:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return None


def validate_user_message(text: str, max_length: int = 8000) -> str:
    cleaned = sanitize_text(text, max_length=max_length)
    if detect_prompt_injection(cleaned):
        raise GuardrailError(
            "Your message was blocked by safety filters. Please rephrase your question."
        )
    return cleaned
