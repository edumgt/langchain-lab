import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def env(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key)
    return v if v is not None and v != "" else default

APP_ENV = env("APP_ENV", "dev")
LOG_LEVEL = env("LOG_LEVEL", "INFO")

LLM_PROVIDER = env("LLM_PROVIDER", "auto")

OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = env("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_EMBED_MODEL = env("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_TIMEOUT_SEC = int(env("OLLAMA_TIMEOUT_SEC", "120") or "120")

OPENAI_COMPAT_BASE_URL = env("OPENAI_COMPAT_BASE_URL", "http://host.docker.internal:1234/v1")
OPENAI_COMPAT_API_KEY = env("OPENAI_COMPAT_API_KEY", "lm-studio")
OPENAI_COMPAT_MODEL = env("OPENAI_COMPAT_MODEL", "gpt-4o-mini")

OPENAI_API_KEY = env("OPENAI_API_KEY", "")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-4o-mini")

RAG_ENABLED = (env("RAG_ENABLED", "true") or "true").lower() == "true"
CHROMA_PERSIST_DIR = env("CHROMA_PERSIST_DIR", str(PROJECT_ROOT / "storage" / "chroma"))
DOCS_DIR = env("DOCS_DIR", str(PROJECT_ROOT / "data" / "docs"))
CHUNK_SIZE = int(env("CHUNK_SIZE", "900") or "900")
CHUNK_OVERLAP = int(env("CHUNK_OVERLAP", "150") or "150")
TOP_K = int(env("TOP_K", "5") or "5")

LANGCHAIN_TRACING_V2 = (env("LANGCHAIN_TRACING_V2", "false") or "false").lower() == "true"
LANGCHAIN_API_KEY = env("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = env("LANGCHAIN_PROJECT", "langchain-catalog-lab")

# Langfuse — LLM Observability (tracing, cost, prompt management, eval)
LANGFUSE_SECRET_KEY = env("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = env("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_HOST = env("LANGFUSE_HOST", "https://cloud.langfuse.com")
