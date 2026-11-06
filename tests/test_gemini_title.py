from types import SimpleNamespace

from kevin.services.gemini.service import GeminiService
from kevin.settings import settings


def _fake_response(text: str):
    return SimpleNamespace(
        candidates=[
            SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(text=text)]))
        ]
    )


def test_generate_title_cleans_model_output(monkeypatch, session):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    service = GeminiService(session=session, user_id=1, year=2026, month=1)
    monkeypatch.setattr(
        service,
        "_generate_with_retry",
        lambda *args, **kwargs: _fake_response('  "Grocery   Expense."  '),
    )

    assert service._generate_title("add 50 for groceries") == "Grocery Expense"


def test_generate_title_returns_none_without_text(monkeypatch, session):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    service = GeminiService(session=session, user_id=1, year=2026, month=1)
    monkeypatch.setattr(
        service,
        "_generate_with_retry",
        lambda *args, **kwargs: SimpleNamespace(candidates=[]),
    )

    assert service._generate_title("hi") is None
