from __future__ import annotations
import os, json, time, re, hashlib
from typing import Any, Dict, List, Optional

from app.core.settings import PROJECT_ROOT
BASE_DIR = os.getenv("PROPOSAL_DIR", str(PROJECT_ROOT / "storage" / "proposals"))
INDEX_PATH = os.path.join(BASE_DIR, "index.json")

DEFAULT_TEMPLATE_VERSION = os.getenv("PROPOSAL_TEMPLATE_VERSION", "v11")

def _slug(s: str, max_len: int = 40) -> str:
    s = (s or "proposal").strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^A-Za-z0-9가-힣\-_.]", "", s)
    return s[:max_len] or "proposal"

def _load_index() -> dict:
    os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump({"items":[]}, f, ensure_ascii=False, indent=2)
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_index(idx: dict):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)

def _sha1(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8", errors="ignore")).hexdigest()

def save_markdown(
    sponsor: str,
    campaign: str,
    markdown: str,
    tool_data: dict | None = None,
    used_docs: list | None = None,
    tags: list[str] | None = None,
    template_version: str | None = None,
) -> dict:
    ts = int(time.time())
    folder = f"{ts}_{_slug(sponsor)}_{_slug(campaign)}"
    out_dir = os.path.join(BASE_DIR, folder)
    os.makedirs(out_dir, exist_ok=True)

    md_path = os.path.join(out_dir, "proposal.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown or "")

    meta = {
        "id": folder,
        "created_at": ts,
        "sponsor": sponsor,
        "campaign": campaign,
        "sha1": _sha1(markdown),
        "paths": {"md": md_path, "pdf": os.path.join(out_dir, "proposal.pdf")},
        "tool_data": tool_data or {},
        "used_docs": used_docs or [],
        "tags": tags or [],
        "template_version": template_version or DEFAULT_TEMPLATE_VERSION,
        "status": "draft",
        "approved_at": None,
        "approved_by": None,
    }

    idx = _load_index()
    items = idx.get("items", []) or []
    items.append({k: meta[k] for k in ["id","created_at","sponsor","campaign","sha1","paths","tags","template_version","status","approved_at","approved_by"]})
    idx["items"] = sorted(items, key=lambda x: x.get("created_at",0), reverse=True)
    _save_index(idx)
    return meta

def mark_approved(version_id: str, approved_by: str | None = None) -> dict:
    idx = _load_index()
    items = idx.get("items", []) or []
    now = int(time.time())
    for it in items:
        if it.get("id") == version_id:
            it["status"] = "approved"
            it["approved_at"] = now
            it["approved_by"] = approved_by
            break
    idx["items"] = items
    _save_index(idx)
    return {"id": version_id, "approved_at": now, "approved_by": approved_by}

def list_versions(limit: int = 50) -> list:
    idx = _load_index()
    return (idx.get("items", []) or [])[:limit]
