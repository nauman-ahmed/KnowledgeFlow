import json
import re

from openai import OpenAI

from app.core.config import get_settings
from app.core.llm import get_openai_client
from app.ontology.loader import OntologyLoader, get_ontology
from app.ontology.prompts import build_extraction_system_prompt, build_extraction_user_prompt
from app.ontology.schemas import ExtractionResult

EXTRACTION_JSON_INSTRUCTION = (
    "Return ONLY valid JSON with this exact shape:\n"
    "{\n"
    '  "entities": [{"type": "Concept", "name": "compound interest", "uri": null}],\n'
    '  "relations": [{\n'
    '    "predicate": "relatedTo",\n'
    '    "source_type": "Concept",\n'
    '    "source_name": "compound interest",\n'
    '    "target_type": "Concept",\n'
    '    "target_name": "simple interest"\n'
    "  }],\n"
    '  "citations": [{"text": "Smith et al. 2020", "context": "optional surrounding text"}]\n'
    "}\n"
    "Use null for uri when not applicable. Do not wrap JSON in markdown fences."
)


def _parse_json_response(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _validate_extraction(data: dict, loader: OntologyLoader) -> ExtractionResult:
    allowed_types = set(loader.extractable_entity_types())
    allowed_predicates = set(loader.extractable_relationships())
    result = ExtractionResult.model_validate(data)
    for entity in result.entities:
        if entity.type not in allowed_types:
            raise ValueError(f"Unsupported entity type: {entity.type}")
    for relation in result.relations:
        if relation.predicate not in allowed_predicates:
            raise ValueError(f"Unsupported relationship predicate: {relation.predicate}")
    return result


def extract_from_chunk(
    *,
    document_title: str,
    document_filename: str,
    chunk_text: str,
    client: OpenAI | None = None,
    loader: OntologyLoader | None = None,
) -> ExtractionResult:
    settings = get_settings()
    llm = client or get_openai_client()
    ont = loader or get_ontology()

    system_prompt = build_extraction_system_prompt(ont)
    user_prompt = build_extraction_user_prompt(
        document_title=document_title,
        document_filename=document_filename,
        chunk_text=chunk_text,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {"role": "user", "content": EXTRACTION_JSON_INSTRUCTION},
    ]

    response = llm.chat.completions.create(
        model=settings.llm_chat_model,
        messages=messages,
        max_tokens=1200,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    data = _parse_json_response(raw)
    return _validate_extraction(data, ont)
