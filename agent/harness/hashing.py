import hashlib
import json

from contracts.schemas import CodeSnippet, DetectedLanguage


def canonical_output_hash(
    language: DetectedLanguage,
    explanation: str,
    documentation: str,
) -> str:
    canonical = json.dumps(
        {
            "language_name": language.name,
            "explanation": explanation,
            "documentation": documentation,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def canonical_snippet_hash(snippet: CodeSnippet) -> str:
    canonical = json.dumps(
        {
            "code": snippet.code,
            "source_id": snippet.source_id,
            "submitted_at": snippet.submitted_at.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()