from __future__ import annotations
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from app.core.llm_factory import build_embeddings
from app.core import settings

def load_documents(docs_dir: str):
    docs = []
    for root, _, files in os.walk(docs_dir):
        if os.path.basename(root).startswith("."):
            continue
        for fn in sorted(files):
            path = os.path.join(root, fn)
            lower = fn.lower()
            try:
                if lower.endswith(".pdf"):
                    docs.extend(PyPDFLoader(path).load())
                elif lower.endswith((".md", ".txt")):
                    loaded = TextLoader(path, encoding="utf-8").load()
                    for d in loaded:
                        d.metadata["filename"] = fn
                        d.metadata["source"] = fn
                    docs.extend(loaded)
            except Exception:
                continue
    return docs

_ingested: set[str] = set()

def ingest_dir(docs_dir: str, persist_dir: str, collection: str) -> int:
    key = f"{docs_dir}::{collection}"
    if key in _ingested:
        return 0
    docs = load_documents(docs_dir)
    if not docs:
        return 0
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
    chunks = splitter.split_documents(docs)
    vs = Chroma(persist_directory=persist_dir, embedding_function=build_embeddings(), collection_name=collection)
    vs.delete_collection()
    vs = Chroma(persist_directory=persist_dir, embedding_function=build_embeddings(), collection_name=collection)
    vs.add_documents(chunks)
    vs.persist()
    _ingested.add(key)
    return len(chunks)

def vectorstore(persist_dir: str, collection: str):
    return Chroma(persist_directory=persist_dir, embedding_function=build_embeddings(), collection_name=collection)


# --- v8: metadata sidecar support for Self-Query Retriever ---
import json
import re
from datetime import datetime

META_DIRNAME = ".meta"
META_INDEX = "index.json"

def _meta_index_path(docs_dir: str) -> str:
    return os.path.join(docs_dir, META_DIRNAME, META_INDEX)

def load_meta_index(docs_dir: str) -> dict:
    path = _meta_index_path(docs_dir)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_meta_index(docs_dir: str, idx: dict) -> None:
    meta_dir = os.path.join(docs_dir, META_DIRNAME)
    os.makedirs(meta_dir, exist_ok=True)
    path = _meta_index_path(docs_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)

def infer_metadata_from_filename(filename: str) -> dict:
    """학습용: 파일명 기반 메타데이터 추정(운영에서는 본문/헤더 추출로 고도화)."""
    lower = filename.lower()
    if any(k in lower for k in ["policy", "규정", "개인정보", "privacy"]):
        doc_type = "policy"
    elif any(k in lower for k in ["press", "pr", "보도", "release"]):
        doc_type = "pr"
    elif any(k in lower for k in ["proposal", "후원", "제안", "sponsor"]):
        doc_type = "proposal"
    else:
        doc_type = "general"

    year = None
    m = re.search(r"(20\d{2})", filename)
    if m:
        try:
            year = int(m.group(1))
        except Exception:
            year = None
    if year is None:
        year = datetime.now().year

    # org heuristic
    org = "artbiz-org"
    if any(k in lower for k in ["festival", "페스티벌"]):
        org = "festival-org"
    elif any(k in lower for k in ["museum", "미술관"]):
        org = "museum-org"
    elif any(k in lower for k in ["theatre", "극장"]):
        org = "theatre-org"

    return {"type": doc_type, "year": year, "org": org, "filename": filename}

def load_documents_meta(docs_dir: str):
    docs = load_documents(docs_dir)
    idx = load_meta_index(docs_dir)
    # merge sidecar metadata by basename of 'source'
    for d in docs:
        src = (d.metadata or {}).get("source", "") or ""
        bn = os.path.basename(src)
        if bn in idx:
            d.metadata = {**(d.metadata or {}), **idx[bn]}
    return docs

def ingest_dir_meta(docs_dir: str, persist_dir: str, collection: str) -> int:
    docs = load_documents_meta(docs_dir)
    if not docs:
        return 0
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
    chunks = splitter.split_documents(docs)
    vs = Chroma(persist_directory=persist_dir, embedding_function=build_embeddings(), collection_name=collection)
    vs.add_documents(chunks)
    vs.persist()
    return len(chunks)
