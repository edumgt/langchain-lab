from __future__ import annotations
import os
import json
import datetime
from fastapi import Request
from starlette.responses import RedirectResponse
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

from app.server.docs_api import router as docs_router
from app.server.self_query_api import router as rag_router
from app.server.proposal_api import router as artbiz_router
from fastapi.middleware.cors import CORSMiddleware

from app.server.models import ChatRequest, ChatResponse, ApproveRequest, ApproveResponse
from fastapi import UploadFile, File
from fastapi.responses import RedirectResponse
from app.server.metadata_extractor import build_sidecar_meta
from app.server.self_query_parser import parse_self_query
from app.server.index_queue import enqueue, read_jobs
from app.server.proposal_store import save_markdown, list_versions, mark_approved
from app.server.pdf_renderer import render_markdown_to_pdf
from app.server.proposal_template import template_markdown_skeleton
from app.server.proposal_normalizer import normalize_to_template, check_structure
from app.server.proposal_section_rewriter import rewrite_sections_llm, assemble_fixed_template_md
from app.server.proposal_consistency import overall as consistency_overall
from app.server.proposal_citation_enforcer import enforce_section_citations, citation_placement_check
from app.server.proposal_footnotes import apply_footnotes






from app.server.agent import run, answer_rag, answer_chat, answer_plan, stream_chat, stream_rag, stream_plan, route
from app.server.store import get_action, update_status
from app.server.feedback import save_feedback, get_stats as feedback_stats
from app.server.eval import full_report as eval_report

from app.tools.schemas import (
    BudgetSplitRequest, BudgetSplitResponse,
    TimelineRequest, TimelineResponse,
    SponsorshipPackageRequest, SponsorshipPackageResponse,
    ReportRequest, ReportResponse,
)
from app.tools.impl import budget_split, timeline, sponsorship_package, make_report


import shutil

DOCS_DIR = "/app/data/docs"
META_DIR = "/app/data/docs/.meta"
META_INDEX = "/app/data/docs/.meta/index.json"

def _load_index():
    os.makedirs(META_DIR, exist_ok=True)
    if not os.path.exists(META_INDEX):
        with open(META_INDEX, "w", encoding="utf-8") as f:
            json.dump({"docs":[]}, f, ensure_ascii=False, indent=2)
    with open(META_INDEX, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_index(data):
    os.makedirs(META_DIR, exist_ok=True)
    with open(META_INDEX, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _upsert_doc(meta: dict):
    idx = _load_index()
    docs = idx.get("docs", [])
    docs = [d for d in docs if d.get("filename") != meta.get("filename")]
    docs.append(meta)
    idx["docs"] = sorted(docs, key=lambda x: x.get("filename",""))
    _save_index(idx)
    return idx


app = FastAPI(title="주식 AI Agent", version="1.0.0")




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(docs_router)
app.include_router(rag_router)
app.include_router(artbiz_router)


@app.post("/tools/budget-split", response_model=BudgetSplitResponse)
def tools_budget_split(req: BudgetSplitRequest):
    return budget_split(req)

@app.post("/tools/timeline", response_model=TimelineResponse)
def tools_timeline(req: TimelineRequest):
    return timeline(req)

@app.post("/tools/sponsorship-package", response_model=SponsorshipPackageResponse)
def tools_sponsorship_package(req: SponsorshipPackageRequest):
    return sponsorship_package(req)

@app.post("/tools/report", response_model=ReportResponse)
def tools_report(req: ReportRequest):
    return make_report(req)



@app.post("/docs/upload")
async def docs_upload(request: Request):
    """Upload one or many docs.

    Accepts both:
    - field `file` (single)
    - field `files` (multiple)  # UI에서 multiple 업로드용
    """
    os.makedirs(DOCS_DIR, exist_ok=True)
    form = await request.form()

    upload_files = []
    f1 = form.get("file")
    if f1 is not None:
        upload_files.append(f1)

    try:
        f_list = form.getlist("files")  # type: ignore[attr-defined]
        upload_files.extend(f_list or [])
    except Exception:
        pass

    # filter only UploadFile-like objects
    upload_files = [f for f in upload_files if hasattr(f, "filename") and hasattr(f, "read")]
    if not upload_files:
        raise HTTPException(status_code=422, detail="No files provided. Use form field 'file' or 'files'.")

    saved = []
    for uf in upload_files:
        filename = os.path.basename(getattr(uf, "filename", "uploaded"))
        dest = os.path.join(DOCS_DIR, filename)
        with open(dest, "wb") as fp:
            fp.write(await uf.read())

        meta = build_sidecar_meta(dest)
        _upsert_doc(meta)
        saved.append(meta)

    return {"ok": True, "saved": saved, "count": len(saved)}

@app.get("/docs")
def docs_list():
    idx = _load_index()
    return idx



@app.post("/rag/self-query")
def rag_self_query(payload: dict):
    # expected: { "q": "...", "top_k": 4 }
    q = payload.get("q","")
    if not q:
        raise HTTPException(400, "q is required")
    top_k = int(payload.get("top_k") or 4)

    parsed = parse_self_query(q)

    # use parsed filters
    from app.core import settings
    from app.core.rag_utils import ingest_dir, vectorstore
    _ = ingest_dir(settings.DOCS_DIR, settings.CHROMA_PERSIST_DIR, collection="catalog_docs")
    vs = vectorstore(settings.CHROMA_PERSIST_DIR, collection="catalog_docs")

    # chroma where filter
    where = {}
    if parsed.doc_type:
        where["type"] = parsed.doc_type
    if parsed.year:
        where["year"] = parsed.year
    if parsed.org:
        where["org"] = parsed.org

    docs = vs.similarity_search(parsed.rewritten_query, k=top_k, filter=where or None)
    used = [{"meta": d.metadata, "preview": d.page_content[:220]} for d in docs]

    return {
        "q": q,
        "parsed": parsed.model_dump(),
        "where_filter": where,
        "docs": used,
    }



@app.get("/artbiz/proposals")
def artbiz_proposals():
    return {"ok": True, "items": list_versions(100)}



@app.get("/artbiz/proposal/template")
def artbiz_proposal_template():
    return {"ok": True, "template": template_markdown_skeleton()}

@app.post("/artbiz/proposal/check")
def artbiz_proposal_check(payload: dict):
    md = payload.get("markdown","")
    return {"ok": True, "check": check_structure(md)}


@app.post("/feedback")
def feedback(payload: dict):
    q = payload.get("q", "")
    mode = payload.get("mode", "rag")
    rating = int(payload.get("rating", 1))
    used_docs = payload.get("used_docs", [])
    if rating not in (1, -1):
        raise HTTPException(status_code=422, detail="rating must be 1 or -1")
    entry = save_feedback(q, mode, rating, used_docs)
    return {"ok": True, "id": entry["id"]}


@app.get("/feedback/stats")
def feedback_stats_endpoint():
    return feedback_stats()


@app.get("/eval")
def eval_endpoint(total_responses: int = 0):
    return eval_report(total_responses)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/docs/titles")
def docs_titles():
    """Return {filename: first_heading} for all .md files in DOCS_DIR."""
    import re
    result = {}
    docs_dir = DOCS_DIR
    try:
        for fname in sorted(os.listdir(docs_dir)):
            if not fname.endswith(".md"):
                continue
            path = os.path.join(docs_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("#"):
                            title = re.sub(r"^#+\s*", "", line)
                            result[fname] = title
                            break
            except Exception:
                result[fname] = fname
    except Exception:
        pass
    return result

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    import asyncio

    r = route(req.q) if not req.mode else None
    chosen = req.mode or r.mode

    routed_by = "user" if req.mode else "default"
    if not req.mode:
        from app.server.feedback import preferred_mode_for
        fb_mode = preferred_mode_for(req.q)
        if fb_mode:
            chosen = fb_mode
            routed_by = "feedback"

    async def generate():
        yield json.dumps({"type": "start", "mode": chosen, "routed_by": routed_by}) + "\n"

        if chosen == "rag":
            gen = stream_rag(req.q, top_k=req.top_k)
        elif chosen == "plan":
            gen = stream_plan(req.q)
        else:
            gen = stream_chat(req.q)

        # keepalive: 데이터가 없는 동안 3초마다 ping 전송해 브라우저 timeout 방지
        queue: asyncio.Queue = asyncio.Queue()

        async def fill():
            try:
                async for line in gen:
                    await queue.put(line)
            except Exception as e:
                await queue.put(json.dumps({"type": "error", "message": str(e)}) + "\n")
            await queue.put(None)  # sentinel

        task = asyncio.create_task(fill())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=3.0)
                    if item is None:
                        break
                    yield item
                except asyncio.TimeoutError:
                    yield json.dumps({"type": "ping"}) + "\n"
        finally:
            await task

        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        out = run(req.q, mode=req.mode, top_k=req.top_k, auto_approve=req.auto_approve)
        return ChatResponse(**out)
    except Exception as e:
        msg = str(e)
        if "not found" in msg and "model" in msg.lower():
            friendly = f"Ollama 모델이 아직 준비되지 않았습니다. 잠시 후 다시 시도해 주세요.\n\n기술 정보: {msg}"
        elif "connection" in msg.lower() or "refused" in msg.lower():
            friendly = "Ollama 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해 주세요."
        else:
            friendly = f"처리 중 오류가 발생했습니다: {msg}"
        raise HTTPException(status_code=500, detail=friendly)

@app.post("/approve", response_model=ApproveResponse)
def approve(req: ApproveRequest):
    action = get_action(req.action_id)
    if not action:
        raise HTTPException(404, "action not found")

    token_env = os.getenv("APPROVE_TOKEN","YES")
    if req.token is not None and req.token != token_env:
        raise HTTPException(403, "invalid token")

    if req.approve:
        update_status(req.action_id, "approved")
        # 실행: 승인된 q를 실제 수행(간단히 suggested_mode대로)
        payload = action["payload"]
        mode = payload.get("suggested_mode","rag")
        q = payload.get("q","")
        if mode == "chat":
            ans, used = answer_chat(q)
        elif mode == "plan":
            ans, used = answer_plan(q)
        else:
            ans, used = answer_rag(q)

        update_status(req.action_id, "done")
        return ApproveResponse(ok=True, message="approved and executed", action={"id": req.action_id, "status":"done", "answer": ans, "used_docs": used})

    update_status(req.action_id, "rejected")
    return ApproveResponse(ok=True, message="rejected", action={"id": req.action_id, "status":"rejected"})

# --- UI (Static) ---
app.mount("/ui", StaticFiles(directory="/app/app/server/static", html=True), name="static")

@app.get("/")
def root():
    return RedirectResponse("/ui")
