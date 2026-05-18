from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal, Optional, Tuple, List, Dict

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
    "한국 주식시장과 글로벌 투자를 중심으로 명확하고 실용적인 답변을 제공한다.\n"
    "- 리스크도 반드시 함께 언급한다.\n"
    "- 과장된 수익률 예측은 하지 않는다.\n"
    "- 마크다운 형식으로 구조적으로 답한다."
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
    "너는 주식·투자분석 교재(CONTEXT)를 기반으로만 답하는 AI다.\n"
    "- CONTEXT에 근거가 없으면 '해당 교재에 관련 내용이 없습니다'라고 답한다.\n"
    "- 마지막에 **출처** 섹션을 만들고 SOURCE를 짧게 인용·요약한다.\n"
    "- 숫자·공식·사실은 CONTEXT에서만 가져온다.\n"
    "- 마크다운 형식으로 구조적으로 답한다."
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
    "사용자의 목표와 질문을 바탕으로 구체적인 투자 전략과 실행 계획을 작성하라.\n"
    "출력 형식:\n"
    "1) 전략 요약\n"
    "2) 자산배분 제안 (표 형식)\n"
    "3) 실행 체크리스트\n"
    "4) 리스크 및 대응 방안\n"
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
# Public entry
# ---------------------------------------------------------------------

def run(
    q: str,
    mode: Optional[Mode] = None,
    top_k: Optional[int] = None,
    auto_approve: Optional[bool] = None,
) -> Dict[str, Any]:
    r = route(q)
    chosen: Mode = mode or r.mode

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
    }
