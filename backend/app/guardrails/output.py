import json
import re

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.chat import SourceCitation
from app.schemas.structured import StructuredAnswerResponse

STRUCTURED_INSTRUCTION = (
    "Produce your final answer as ONLY valid JSON with this exact shape:\n"
    "{\n"
    '  "summary": "markdown answer for the user",\n'
    '  "key_points": ["bullet one", "bullet two"],\n'
    '  "sources": [{"document": "filename.ext", "excerpt": "short excerpt"}],\n'
    '  "confidence": "high" | "medium" | "low"\n'
    "}\n"
    "Use only sources supported by the retrieved context. "
    "Cite a document only if your answer actually uses it. "
    "If the retrieved context does not contain the answer, say so in the summary, "
    'set "confidence" to "low" and return "sources": []. '
    "Do not wrap JSON in markdown fences."
)


def _parse_json_response(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _merge_sources(
    parsed: StructuredAnswerResponse,
    fallback_sources: list[SourceCitation],
) -> StructuredAnswerResponse:
    if parsed.sources:
        return parsed
    # A low-confidence answer is usually "the library doesn't cover this";
    # citing every retrieved chunk there would claim support that isn't real.
    if parsed.confidence == "low":
        return parsed
    return parsed.model_copy(update={"sources": fallback_sources})


def generate_structured_answer(
    client: OpenAI,
    answer_messages: list[dict[str, str]],
    fallback_sources: list[SourceCitation],
    max_retries: int | None = None,
) -> StructuredAnswerResponse:
    settings = get_settings()
    attempts = max_retries or settings.structured_output_max_retries
    messages = [*answer_messages, {"role": "user", "content": STRUCTURED_INSTRUCTION}]

    last_error: Exception | None = None
    for _attempt in range(attempts):
        try:
            response = client.chat.completions.create(
                model=settings.llm_chat_model,
                messages=messages,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            data = _parse_json_response(raw)
            parsed = StructuredAnswerResponse.model_validate(data)
            return _merge_sources(parsed, fallback_sources)
        except (ValidationError, json.JSONDecodeError, KeyError) as exc:
            last_error = exc
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous response was invalid JSON or missing required fields. "
                        "Return ONLY corrected JSON matching the schema."
                    ),
                }
            )

    if last_error:
        raise last_error
    raise RuntimeError("Structured output generation failed")


def stream_summary_text(summary: str, chunk_size: int = 16):
    for start in range(0, len(summary), chunk_size):
        yield summary[start : start + chunk_size]
