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
    """Adapter for Langfuse SDK v3+/v4 observation API.

    Children are created from the root span explicitly instead of relying on
    OpenTelemetry's "current span" context. The chat stream is a generator that
    Starlette advances on different threadpool workers, each in a fresh
    context, so context-based parenting would orphan every child span.
    """

    def __init__(self, client: Any, root_span: Any, attributes: dict[str, Any]) -> None:
        self._client = client
        self._root_span = root_span
        self._attributes = attributes

    def span(
        self,
        *,
        name: str,
        metadata: dict[str, Any] | None = None,
        as_type: ObservationType = "span",
    ) -> Any:
        from langfuse import propagate_attributes

        # Entered and exited within this call, so it never spans a yield.
        with propagate_attributes(**self._attributes):
            return self._root_span.start_observation(
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

        from langfuse import propagate_attributes

        attributes = {"user_id": user_id, "session_id": session_id, "metadata": metadata}
        # Not start_as_current_observation: that attaches OTel context on one
        # thread and detaches it on another when used across generator yields.
        with propagate_attributes(**attributes):
            root_span = self._client.start_observation(name=name, as_type="span", input=input)

        try:
            yield _LangfuseTraceWrapper(self._client, root_span, attributes)
        except BaseException as exc:
            root_span.update(level="ERROR", status_message=str(exc) or type(exc).__name__)
            raise
        finally:
            root_span.end()
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
