from pathlib import Path
import pytest

from app.core import llm_factory, settings


def test_project_root_and_default_paths():
    assert settings.PROJECT_ROOT.is_dir()
    assert (settings.PROJECT_ROOT / "app").is_dir()
    assert Path(settings.DOCS_DIR).name == "docs"
    assert Path(settings.CHROMA_PERSIST_DIR).name == "chroma"


def test_pick_provider_explicit(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai_compatible")
    assert llm_factory.pick_provider() == "openai_compatible"

    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    assert llm_factory.pick_provider() == "openai"

    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")
    assert llm_factory.pick_provider() == "ollama"


def test_build_chat_model_openai_requires_key(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm_factory.build_chat_model()
