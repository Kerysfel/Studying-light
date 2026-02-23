"""Utilities for robust JSON extraction from GPT text output."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
SMART_QUOTES_TRANSLATION = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "„": '"',
        "‟": '"',
        "«": '"',
        "»": '"',
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
    }
)


class GptJsonParseError(ValueError):
    """Raised when GPT output cannot be parsed as JSON."""


def _parse_json_candidate(candidate: str) -> object | None:
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _normalize_typographic_quotes(text: str) -> str:
    return text.translate(SMART_QUOTES_TRANSLATION)


def _parse_with_fallback_normalization(candidate: str) -> object | None:
    parsed = _parse_json_candidate(candidate)
    if parsed is not None:
        return parsed

    normalized = _normalize_typographic_quotes(candidate)
    if normalized == candidate:
        return None
    return _parse_json_candidate(normalized)


def _iter_decoder_candidates(raw_text: str) -> Iterable[str]:
    decoder = json.JSONDecoder()
    for start_index, char in enumerate(raw_text):
        if char not in "{[":
            continue
        try:
            _, end_index = decoder.raw_decode(raw_text[start_index:])
        except json.JSONDecodeError:
            continue
        yield raw_text[start_index : start_index + end_index]


def parse_gpt_json_output(raw_output: str) -> object:
    """Extract and parse JSON from GPT output text."""
    text = raw_output.lstrip("\ufeff").strip()
    if not text:
        raise GptJsonParseError("JSON payload is empty")

    direct_value = _parse_with_fallback_normalization(text)
    if direct_value is not None:
        return direct_value

    for fence_match in CODE_FENCE_PATTERN.finditer(text):
        fenced_candidate = fence_match.group(1).strip()
        if not fenced_candidate:
            continue
        fenced_value = _parse_with_fallback_normalization(fenced_candidate)
        if fenced_value is not None:
            return fenced_value

    for candidate in _iter_decoder_candidates(text):
        parsed = _parse_with_fallback_normalization(candidate)
        if parsed is not None:
            return parsed

    raise GptJsonParseError("Invalid JSON syntax")


def parse_gpt_json(raw_output: str) -> object:
    """Backward-compatible alias used by runtime checks/scripts."""
    return parse_gpt_json_output(raw_output)
