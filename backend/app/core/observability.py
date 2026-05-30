"""Langfuse tracing — no-op when keys are not configured."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Literal

from app.core.config import get_settings

ObservationType = Literal[
    "span", "generation", "retriever", "agent", "tool", "chain", "evaluator", "guardrail"
]


class _NoOpSpan:
    def update(self, **kwargs: Any) -> None:
        pass

    def end(self, **kwargs: Any) -> None:
        pass


class _NoOpTrace:
    def span(self, **kwargs: Any) -> _NoOpSpan:
        return _NoOpSpan()

    def update(self, **kwargs: Any) -> None:
        pass


class _LangfuseTraceWrapper:
    """Adapter for Langfuse SDK v3+/v4 observation API."""

    def __init__(self, client: Any, root_span: Any) -> None:
        self._client = client
        self._root_span = root_span

    def span(
        self,
        *,
        name: str,
        metadata: dict[str, Any] | None = None,
        as_type: ObservationType = "span",
    ) -> Any:
        return self._client.start_observation(
            name=name,
            metadata=metadata,
            as_type=as_type,
        )

    def update(self, **kwargs: Any) -> None:
        self._root_span.update(**kwargs)


class LangfuseTracer:
    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = bool(settings.langfuse_public_key and settings.langfuse_secret_key)
        self._client: Any = None
        if self._enabled:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @contextmanager
    def trace(
        self,
        name: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        input: Any = None,
    ) -> Generator[Any, None, None]:
        if not self._enabled or self._client is None:
            yield _NoOpTrace()
            return

        with self._client.start_as_current_observation(
            name=name,
            as_type="span",
            input=input,
        ) as root_span:
            from langfuse import propagate_attributes

            with propagate_attributes(
                user_id=user_id,
                session_id=session_id,
                metadata=metadata,
            ):
                yield _LangfuseTraceWrapper(self._client, root_span)

        self._client.flush()

    def flush(self) -> None:
        if self._client is not None:
            self._client.flush()


_tracer: LangfuseTracer | None = None


def get_tracer() -> LangfuseTracer:
    global _tracer
    if _tracer is None:
        _tracer = LangfuseTracer()
    return _tracer
