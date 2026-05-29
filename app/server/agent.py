from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Literal, Optional, Tuple, List, Dict

from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate

from app.core import settings
from app.core.llm_factory import build_chat_model
from app.core.rag_utils import ingest_dir, vectorstore
from app.server.store import create_action


Mode = Literal["chat", "rag", "plan"]


class Route(BaseModel):
    mode: Mode = Field(description="처리 모드: chat|rag|plan")
    need_approval: bool = Field(description="승인 필요 여부")
    action_type: str = Field(default="none")
    reason: str = Field(default="")


@dataclass
class RAGResult:
    answer: str
    used_docs: List[Dict[str, Any]]


# ---------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------

def route(q: str) -> Route:
    q_l = (q or "").lower()

    plan_keys = [
        "포트폴리오", "자산배분", "투자계획", "리밸런싱", "전략", "백테스트",
        "allocation", "portfolio", "rebalance", "전략 짜", "계획 세워",
    ]
    rag_keys = [
        "근거", "출처", "문서", "재무제표", "지표", "밸류에이션", "valuation",
        "분석", "계산", "공식", "이론", "정의", "설명해줘", "요약", "뭐야", "뭔가요",
        "psr", "per", "pbr", "roe", "roa", "ebitda", "dcf", "capm", "beta",
        "손익", "대차", "현금흐름", "etf", "배당", "선물", "옵션", "채권",
    ]

    if any(k in q for k in plan_keys) or any(k in q_l for k in plan_keys):
        mode: Mode = "plan"
        reason = "포트폴리오/자산배분/투자전략 키워드 감지"
    elif any(k in q for k in rag_keys) or any(k in q_l for k in rag_keys):
        mode = "rag"
        reason = "교재/개념/지표 키워드 감지"
    else:
        mode = "chat"
        reason = "일반 질문으로 판단"

    return Route(mode=mode, need_approval=False, action_type="none", reason=reason)


# ---------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------

_CHAT_SYSTEM = (
    "너는 주식·투자분석 AI 어시스턴트다.\n"
    "한국 주식시장과 글로벌 투자를 중심으로 명확하고 실용적인 답변을 제공한다.\n\n"
    "## 반드시 지켜야 할 규칙\n"
    "1. **사실 기반**: 확실하지 않은 수치(주가, 실적, 날짜)는 단정하지 말고 '확인 필요' 또는 '일반적으로'라고 표현한다.\n"
    "2. **리스크 언급**: 모든 투자 관련 답변에 리스크를 반드시 포함한다.\n"
    "3. **수익률 과장 금지**: '반드시 오른다', '확실한 수익' 같은 표현은 절대 사용하지 않는다.\n"
    "4. **모를 때 인정**: 최신 시세·구체적 종목 추천 등 알 수 없는 정보는 '현재 시점의 정보를 알 수 없다'고 명시한다.\n"
    "5. **마크다운 구조**: 제목·목록·표를 활용해 읽기 쉽게 구성한다."
)


def answer_chat(q: str) -> Tuple[str, List[Dict[str, Any]]]:
    llm = build_chat_model(temperature=0.2)
    resp = llm.invoke(
        [
            {"role": "system", "content": _CHAT_SYSTEM},
            {"role": "user", "content": q},
        ]
    )
    return getattr(resp, "content", str(resp)), []


# ---------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------

_RAG_SYSTEM = (
    "너는 주식·투자분석 교재(CONTEXT)를 기반으로만 답하는 AI다.\n\n"
    "## 반드시 지켜야 할 규칙\n"
    "1. **CONTEXT 외 사실 금지**: CONTEXT에 없는 수치·사실을 절대 추가하지 않는다. 위반 시 할루시네이션이다.\n"
    "2. **근거 없으면 인정**: CONTEXT에 관련 내용이 없으면 '해당 교재에 관련 내용이 없습니다. 다른 출처를 확인하세요.'라고 답한다.\n"
    "3. **직접 인용 우선**: 공식·수치·정의는 CONTEXT 원문을 가능한 한 그대로 인용한다.\n"
    "4. **출처 명시**: 답변 마지막에 **📚 출처** 섹션을 만들고 사용한 SOURCE 번호와 핵심 내용을 한 줄씩 요약한다.\n"
    "5. **추측 표시**: CONTEXT를 해석·추론한 내용은 '(해석)' 또는 '(추론)'을 앞에 붙인다.\n"
    "6. **마크다운 구조**: 제목·목록·표를 활용해 읽기 쉽게 구성한다."
)


def _build_rag_context(docs: list[Any], max_sources: int = 3) -> str:
    picked = docs[:max_sources]
    parts = []
    for i, d in enumerate(picked, start=1):
        parts.append(f"SOURCE {i}:\n{d.page_content}")
    return "\n\n".join(parts)


def answer_rag(q: str, top_k: Optional[int] = None) -> Tuple[str, List[Dict[str, Any]]]:
    ingest_dir(settings.DOCS_DIR, settings.CHROMA_PERSIST_DIR, collection="stock_docs")

    vs = vectorstore(settings.CHROMA_PERSIST_DIR, collection="stock_docs")
    k = int(top_k or settings.TOP_K)
    docs = vs.similarity_search(q, k=k)

    llm = build_chat_model(temperature=0)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _RAG_SYSTEM),
            ("human", "CONTEXT:\n{context}\n\nQ:\n{q}"),
        ]
    )

    context = _build_rag_context(docs, max_sources=3)
    resp = (prompt | llm).invoke({"context": context, "q": q})

    used = [
        {"meta": getattr(d, "metadata", {}), "preview": (d.page_content or "")[:200]}
        for d in docs[:3]
    ]
    return getattr(resp, "content", str(resp)), used


# ---------------------------------------------------------------------
# Plan (portfolio / strategy)
# ---------------------------------------------------------------------

_PLAN_SYSTEM = (
    "너는 주식·투자 포트폴리오 전략가 AI다.\n"
    "사용자의 목표와 질문을 바탕으로 구체적인 투자 전략과 실행 계획을 작성하라.\n\n"
    "## 반드시 지켜야 할 규칙\n"
    "1. **가정 명시**: 수익률·비중 수치를 제시할 때 반드시 '가정:' 또는 '역사적 평균 기준'임을 명시한다.\n"
    "2. **미래 예측 금지**: '반드시', '확실히' 같은 확언 표현을 사용하지 않는다. '기대 가능', '가능성 있음'으로 표현한다.\n"
    "3. **리스크 섹션 필수**: 모든 전략 플랜에 리스크 및 대응 방안 섹션을 포함한다.\n"
    "4. **투자 주의 문구**: 답변 마지막에 '※ 이 전략은 참고용이며 투자 손실에 대한 책임은 투자자 본인에게 있습니다.'를 항상 추가한다.\n\n"
    "## 출력 형식\n"
    "1) 전략 요약\n"
    "2) 자산배분 제안 (표 형식, 비중·기대수익·리스크 포함)\n"
    "3) 실행 체크리스트\n"
    "4) 리스크 및 대응 방안\n"
    "5) 투자 주의 문구\n\n"
    "모든 수치와 전략 근거는 명확히 설명하라. 마크다운 형식으로 작성하라."
)


def answer_plan(q: str) -> Tuple[str, List[Dict[str, Any]]]:
    llm = build_chat_model(temperature=0.3)
    resp = llm.invoke(
        [
            {"role": "system", "content": _PLAN_SYSTEM},
            {"role": "user", "content": q},
        ]
    )
    used: List[Dict[str, Any]] = []
    return getattr(resp, "content", str(resp)), used


# ---------------------------------------------------------------------
# Streaming variants
# ---------------------------------------------------------------------

async def stream_chat(q: str) -> AsyncIterator[str]:
    llm = build_chat_model(temperature=0.2, streaming=True)
    async for chunk in llm.astream([
        {"role": "system", "content": _CHAT_SYSTEM},
        {"role": "user", "content": q},
    ]):
        content = getattr(chunk, "content", "") or ""
        if content:
            yield json.dumps({"type": "token", "content": content}) + "\n"


async def stream_rag(q: str, top_k: Optional[int] = None) -> AsyncIterator[str]:
    import asyncio
    loop = asyncio.get_event_loop()

    await loop.run_in_executor(
        None,
        lambda: ingest_dir(settings.DOCS_DIR, settings.CHROMA_PERSIST_DIR, collection="stock_docs"),
    )
    vs = vectorstore(settings.CHROMA_PERSIST_DIR, collection="stock_docs")
    k = int(top_k or settings.TOP_K)
    docs = await loop.run_in_executor(None, lambda: vs.similarity_search(q, k=k))

    used = [
        {"meta": getattr(d, "metadata", {}), "preview": (d.page_content or "")[:200]}
        for d in docs[:3]
    ]
    yield json.dumps({"type": "meta", "used_docs": used}) + "\n"

    llm = build_chat_model(temperature=0, streaming=True)
    prompt = ChatPromptTemplate.from_messages([
        ("system", _RAG_SYSTEM),
        ("human", "CONTEXT:\n{context}\n\nQ:\n{q}"),
    ])
    context = _build_rag_context(docs, max_sources=3)
    async for chunk in (prompt | llm).astream({"context": context, "q": q}):
        content = getattr(chunk, "content", "") or ""
        if content:
            yield json.dumps({"type": "token", "content": content}) + "\n"


async def stream_plan(q: str) -> AsyncIterator[str]:
    llm = build_chat_model(temperature=0.3, streaming=True)
    async for chunk in llm.astream([
        {"role": "system", "content": _PLAN_SYSTEM},
        {"role": "user", "content": q},
    ]):
        content = getattr(chunk, "content", "") or ""
        if content:
            yield json.dumps({"type": "token", "content": content}) + "\n"


# ---------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------

def run(
    q: str,
    mode: Optional[Mode] = None,
    top_k: Optional[int] = None,
    auto_approve: Optional[bool] = None,
) -> Dict[str, Any]:
    r = route(q)

    # 사용자가 모드를 직접 선택하지 않은 경우, 피드백 히스토리 기반 모드 우선 적용
    routed_by = "user" if mode else "default"
    if not mode:
        from app.server.feedback import preferred_mode_for
        fb_mode = preferred_mode_for(q)
        if fb_mode:
            chosen: Mode = fb_mode  # type: ignore[assignment]
            routed_by = "feedback"
        else:
            chosen = r.mode
    else:
        chosen = mode

    if chosen == "chat":
        ans, used = answer_chat(q)
    elif chosen == "plan":
        ans, used = answer_plan(q)
    else:
        ans, used = answer_rag(q, top_k=top_k)

    return {
        "answer": ans,
        "mode": chosen,
        "used_docs": used,
        "pending_action": None,
        "routed_by": routed_by,
    }
