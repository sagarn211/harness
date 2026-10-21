from typing import Protocol


class Explainer(Protocol):
    def explain_and_document(self, code: str, language: str) -> tuple[str, str]:
        ...


class StubExplainer:
    def explain_and_document(self, code: str, language: str) -> tuple[str, str]:
        return (
            f"Stub explanation for {language} snippet.",
            f"# {language} documentation stub",
        )


class ExplainError(Exception):
    pass


# Real implementation lives in gemini_explainer.py. Do not import it
# here; it must be imported explicitly by the wiring layer.