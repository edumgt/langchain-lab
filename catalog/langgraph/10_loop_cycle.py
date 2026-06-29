"""LangGraph 10 — 사이클/루프 (재시도 패턴 + 최대 N회 종료)

핵심 개념
──────────
  LangGraph 에서 사이클(cycle)은 노드 → 조건 → 동일 노드(또는 이전 노드)로
  엣지를 연결하면 만들어진다.
  무한루프를 막으려면 state 에 카운터를 두고 조건 함수에서 종료 분기를 만든다.

흐름
────
  generate ─▶ evaluate
                 ├─ "retry"  (품질 부족) ──▶ generate  (루프백)
                 └─ "done"   (품질 충분 또는 max 도달) ──▶ END

언제 쓰나?
──────────
  - LLM 결과물 품질 검증 후 재생성 (Self-Refinement)
  - 외부 API 호출 실패 재시도
  - 조건 달성까지 반복 실행 (탐색, 파싱 재시도 등)

주요 설계 원칙
──────────────
  1. state 에 retry_count 필드를 명시해 루프 횟수를 추적한다.
  2. 조건 함수(route)가 "done" 또는 "retry" 를 반환한다.
  3. MAX_RETRIES 로 무한루프를 방지한다.
  4. 루프 종료 이유(reason)를 state 에 남겨 디버깅에 활용한다.
"""
from __future__ import annotations
from typing import TypedDict, Literal
from rich import print

from langgraph.graph import StateGraph, END

from app.core.llm_factory import build_chat_model
from app.utils.console import header
from catalog.langgraph._viz import render_graph_mermaid

MAX_RETRIES = 3  # 최대 재시도 횟수

# ── 품질 기준 (학습용 단순 규칙) ───────────────────────────────────────────
_MIN_LENGTH = 200   # 최소 글자 수
_REQUIRED_KEYWORDS = ["예산", "일정"]  # 반드시 포함해야 할 키워드


class State(TypedDict):
    question: str
    draft: str
    retry_count: int
    reason: str    # 루프 종료/재시도 이유 (디버깅용)
    final: str


def main():
    header("LANGGRAPH 10 — 사이클/루프 (재시도 패턴)")
    llm = build_chat_model(temperature=0.3)

    # ── generate: 초안 생성 ────────────────────────────────────────────────
    def generate(state: State) -> State:
        retry = state["retry_count"]
        hint = ""
        if retry > 0:
            # 재시도 시 이전 실패 이유를 힌트로 전달해 품질 향상 유도
            hint = f"\n\n[이전 피드백] {state['reason']} — 이 부분을 보완해서 다시 작성하라."
        resp = llm.invoke([
            {"role": "system", "content": "너는 기획 전문가다. 실행 계획 초안을 작성한다."},
            {"role": "user",   "content": state["question"] + hint},
        ])
        draft = getattr(resp, "content", str(resp))
        return {**state, "draft": draft, "retry_count": retry + 1}

    # ── evaluate: 품질 평가 ────────────────────────────────────────────────
    def evaluate(state: State) -> State:
        draft = state["draft"]
        missing_kw = [k for k in _REQUIRED_KEYWORDS if k not in draft]
        too_short = len(draft) < _MIN_LENGTH

        if missing_kw:
            reason = f"필수 키워드 누락: {missing_kw}"
        elif too_short:
            reason = f"분량 부족 ({len(draft)}자 < {_MIN_LENGTH}자)"
        else:
            reason = "품질 기준 충족"

        return {**state, "reason": reason}

    # ── route: 루프 계속 or 종료 결정 ─────────────────────────────────────
    def route(state: State) -> Literal["retry", "done"]:
        if state["retry_count"] >= MAX_RETRIES:
            return "done"   # 최대 횟수 도달 → 강제 종료
        if state["reason"] == "품질 기준 충족":
            return "done"
        return "retry"

    # ── finalize: 최종 정리 ────────────────────────────────────────────────
    def finalize(state: State) -> State:
        suffix = (
            "\n\n---\n✅ 품질 기준 충족"
            if state["reason"] == "품질 기준 충족"
            else f"\n\n---\n⚠️ 최대 재시도({MAX_RETRIES}회) 도달 — 현재 초안으로 종료\n이유: {state['reason']}"
        )
        return {**state, "final": state["draft"] + suffix}

    # ── 그래프 구성 ────────────────────────────────────────────────────────
    g = StateGraph(State)
    g.add_node("generate", generate)
    g.add_node("evaluate", evaluate)
    g.add_node("finalize", finalize)

    g.set_entry_point("generate")
    g.add_edge("generate", "evaluate")

    # 조건 엣지: evaluate → retry(generate 로 루프백) or done(finalize)
    g.add_conditional_edges(
        "evaluate",
        route,
        {"retry": "generate", "done": "finalize"},
    )
    g.add_edge("finalize", END)

    app = g.compile()
    render_graph_mermaid(app, "10_loop_cycle")

    # ── 실행 ──────────────────────────────────────────────────────────────
    init_state: State = {
        "question": "예산 3천만원으로 2주 내 관객개발 캠페인 실행계획을 작성해줘. 일정표 포함.",
        "draft": "",
        "retry_count": 0,
        "reason": "",
        "final": "",
    }
    out = app.invoke(init_state)

    print(f"\n[bold]총 시도 횟수:[/bold] {out['retry_count']}")
    print(f"[bold]종료 이유:[/bold] {out['reason']}")
    print("\n[bold]최종 결과[/bold]")
    print(out["final"])


if __name__ == "__main__":
    main()
