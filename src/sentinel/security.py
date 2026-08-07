from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from sentinel.config import settings


INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_instructions",
        re.compile(
            r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|system|developer)\b.{0,20}\binstructions?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "system_prompt_extraction",
        re.compile(
            r"\b(reveal|show|print|repeat|expose)\b.{0,35}\b(system prompt|developer message|hidden prompt)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "jailbreak_language",
        re.compile(r"\b(jailbreak|do anything now|DAN mode)\b", re.IGNORECASE),
    ),
]


@dataclass
class PreparedInput:
    safe_text: str
    pii_detected_count: int
    pii_entities: list[str]
    security_flags: list[str]


@lru_cache(maxsize=1)
def get_presidio_analyzer() -> AnalyzerEngine:
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [
            {
                "lang_code": "en",
                "model_name": settings.spacy_model,
            }
        ],
    }

    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=["en"],
    )


@lru_cache(maxsize=1)
def get_presidio_anonymizer() -> AnonymizerEngine:
    return AnonymizerEngine()


def remove_prompt_injection_phrases(text: str) -> tuple[str, list[str]]:
    cleaned = text
    flags: list[str] = []

    for flag_name, pattern in INJECTION_PATTERNS:
        if pattern.search(cleaned):
            flags.append(flag_name)
            cleaned = pattern.sub("[BLOCKED_INSTRUCTION]", cleaned)

    return cleaned, flags


def prepare_input(text: str) -> PreparedInput:
    """
    Security boundary before LangGraph/A2A/LLM execution.

    Flow:
      raw text
        -> prompt-injection phrase filtering
        -> Presidio PII detection
        -> Presidio anonymization
        -> safe text enters graph state

    Raw PII is not stored in IncidentState.
    """
    security_cleaned, security_flags = remove_prompt_injection_phrases(text)

    analyzer = get_presidio_analyzer()
    findings = analyzer.analyze(
        text=security_cleaned,
        language="en",
        score_threshold=settings.pii_score_threshold,
    )

    anonymized = get_presidio_anonymizer().anonymize(
        text=security_cleaned,
        analyzer_results=findings,
    )

    entity_types = sorted({result.entity_type for result in findings})

    return PreparedInput(
        safe_text=anonymized.text,
        pii_detected_count=len(findings),
        pii_entities=entity_types,
        security_flags=security_flags,
    )
