import json

from app.core.config import get_settings
from app.core.redis_client import get_redis

SESSION_KEY_PREFIX = "knowledgeflow:session:"


def _session_key(conversation_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{conversation_id}"


def get_session_history(conversation_id: str) -> list[dict[str, str]] | None:
    try:
        raw = get_redis().get(_session_key(conversation_id))
        if not raw:
            return None
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except Exception:
        return None
    return None


def set_session_history(conversation_id: str, messages: list[dict[str, str]]) -> None:
    settings = get_settings()
    limit = settings.chat_history_turns * 2
    trimmed = messages[-limit:] if limit else messages
    try:
        get_redis().set(
            _session_key(conversation_id),
            json.dumps(trimmed),
            ex=settings.session_memory_ttl_seconds,
        )
    except Exception:
        pass


def append_session_turn(
    conversation_id: str,
    user_content: str,
    assistant_content: str,
    existing: list[dict[str, str]] | None = None,
) -> None:
    history = list(existing or get_session_history(conversation_id) or [])
    history.append({"role": "user", "content": user_content})
    history.append({"role": "assistant", "content": assistant_content})
    set_session_history(conversation_id, history)


def clear_session_history(conversation_id: str) -> None:
    try:
        get_redis().delete(_session_key(conversation_id))
    except Exception:
        pass
