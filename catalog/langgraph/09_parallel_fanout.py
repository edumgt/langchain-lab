"""LangGraph 09 — 병렬 팬아웃 / 팬인 (Send API + Annotated reducer)

핵심 개념
──────────
  Send API
    add_conditional_edges 에서 List[Send] 를 반환하면 LangGraph 가
    각 Send 를 독립 태스크로 병렬 디스패치한다.
    Send("node_name", payload_dict) → 해당 노드에 개별 입력을 전달.

  Annotated[list, operator.add]  (reducer)
    같은 키에 여러 노드가 값을 쓸 때 어떻게 합칠지 정의하는 reducer.
    operator.add → 리스트를 이어붙인다(append).
    각 병렬 노드가 ["item"] 을 반환하면 state 에 자동 누적된다.

흐름
────
  __start__
      └─(conditional: dispatch)
            ├─▶ analyze(role="strategy")  ─┐
            ├─▶ analyze(role="marketing") ─┤─(Annotated reducer 누적)─▶ synthesize ─▶ END
            └─▶ analyze(role="ops")       ─┘

언제 쓰나?
──────────
  - 역할별 병렬 분석 후 통합
  - Map-Reduce 스타일 배치 처리
  - 멀티 에이전트 동시 호출 후 수렴
"""
from __future__ import annotations
import operator
from typing import Annotated, TypedDict, List
from rich import print

from langgraph.graph import StateGraph, END
from langgraph.constants import Send

from app.core.llm_factory import build_chat_model
from app.utils.console import header
from catalog.langgraph._viz import render_graph_mermaid


# ── State 정의 ─────────────────────────────────────────────────────────────
class AnalysisItem(TypedDict):
    role: str
    text: str


class State(TypedDict):
    question: str
    # Annotated reducer: 각 analyze 노드가 반환하는 리스트를 자동 누적
    analyses: Annotated[List[AnalysisItem], operator.add]
    final: str


# ── 역할별 시스템 프롬프트 ──────────────────────────────────────────────────
ROLES = {
    "strategy":   "너는 전략 컨설턴트다. 목표·우선순위·핵심 리스크를 3문장으로.",
    "marketing":  "너는 마케팅 리드다.   채널·콘텐츠·전환율 관점을 3문장으로.",
    "ops":        "너는 운영 담당이다.   일정·예산·체크리스트를 3문장으로.",
}


def main():
    header("LANGGRAPH 09 — 병렬 팬아웃 / 팬인 (Send API)")
    llm = build_chat_model(temperature=0.2)

    # ── ① 팬아웃 디스패처 (conditional_edges 에서 호출) ────────────────────
    def dispatch(state: State) -> List[Send]:
        """각 역할을 analyze 노드에 병렬 디스패치한다."""
        return [
            Send("analyze", {"question": state["question"], "role": role})
            for role in ROLES
        ]

    # ── ② 개별 분석 노드 (역할마다 병렬 실행) ──────────────────────────────
    def analyze(inp: dict) -> dict:
        """Send 로 받은 개별 입력으로 역할별 분석 실행."""
        role = inp["role"]
        resp = llm.invoke([
            {"role": "system", "content": ROLES[role]},
            {"role": "user",   "content": inp["question"]},
        ])
        text = getattr(resp, "content", str(resp))
        # Annotated[list, operator.add] 가 이 리스트를 state.analyses 에 누적
        return {"analyses": [AnalysisItem(role=role, text=text)]}

    # ── ③ 팬인: 누적된 분석 결과를 통합 ───────────────────────────────────
    def synthesize(state: State) -> State:
        parts = "\n\n".join(
            f"[{a['role'].upper()}]\n{a['text']}" for a in state["analyses"]
        )
        resp = llm.invoke([
            {"role": "system", "content": (
                "아래 세 가지 관점을 통합해 실행 계획 하나로 정리하라. "
                "표(역할 | 핵심 액션 | 예산 비중 | 기간)를 반드시 포함하라."
            )},
            {"role": "user", "content": f"Q: {state['question']}\n\n{parts}"},
        ])
        return {**state, "final": getattr(resp, "content", str(resp))}

    # ── 그래프 구성 ────────────────────────────────────────────────────────
    g = StateGraph(State)
    g.add_node("analyze", analyze)
    g.add_node("synthesize", synthesize)

    # add_conditional_edges 에서 __start__ 대신 entry_point 역할을 하는
    # 빈 노드를 두고 conditional_edges 로 Send 를 반환하는 패턴
    g.add_node("router", lambda s: s)   # passthrough (그래프 진입점)
    g.set_entry_point("router")
    g.add_conditional_edges("router", dispatch, ["analyze"])

    # 모든 analyze 인스턴스 완료 후 synthesize 로 팬인
    g.add_edge("analyze", "synthesize")
    g.add_edge("synthesize", END)

    app = g.compile()
    render_graph_mermaid(app, "09_parallel_fanout")

    q = "예산 3천만원, 2주, 지역 커뮤니티 협업 관객개발 캠페인 실행 계획"
    out = app.invoke({"question": q, "analyses": [], "final": ""})

    print("\n[bold]병렬 분석 결과 (누적된 analyses)[/bold]")
    for a in out["analyses"]:
        print(f"  [{a['role']}] {a['text'][:80]!r}")

    print("\n[bold]통합 최종 계획 (synthesize)[/bold]")
    print(out["final"])


if __name__ == "__main__":
    main()
