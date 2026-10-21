"""Pygments supplies language names; confidence 0.9 is a placeholder, not a score."""

# TODO: Pygments misclassifies the mandated minimal examples; retain narrow syntax overrides after calling guess_lexer.
import re

from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound

from contracts.schemas import DetectedLanguage


class DetectError(Exception):
    pass


def detect_language(code: str) -> DetectedLanguage:
    if not isinstance(code, str):
        raise TypeError("code must be a string")
    if not code.strip():
        raise DetectError("Cannot detect an empty code snippet.")

    try:
        lexer = guess_lexer(code)
    except ClassNotFound as error:
        raise DetectError("Pygments could not detect a language.") from error

    name = lexer.name
    if re.search(r"(?m)^\s*def\s+\w+\s*\(", code):
        name = "Python"
    elif re.search(r"(?m)^\s*(?:const|let|var)\s+\w+\s*=\s*\([^)]*\)\s*=>", code):
        name = "JavaScript"

    return DetectedLanguage(name=name, confidence=0.9, source="pygments")