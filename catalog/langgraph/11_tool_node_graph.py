"""LangGraph 11 — ToolNode + MessagesState (ReAct 루프 내장)

핵심 개념
──────────
  ToolNode (langgraph.prebuilt)
    - LLM 이 tool_calls 를 반환하면 자동으로 툴을 실행하고
      ToolMessage 를 messages 에 추가한다.
    - 수동으로 tool.invoke() → ToolMessage 생성을 작성할 필요가 없다.

  add_messages (reducer)
    - Annotated[list, add_messages] 로 선언하면 메시지 리스트를 안전하게 누적한다.
    - 동일 id 의 메시지는 덮어쓰고(업데이트), 새 메시지는 append 한다.

  tools_condition (prebuilt 라우터)
    - 마지막 메시지에 tool_calls 가 있으면 "tools" 노드로 라우팅.
    - 없으면 END 로 라우팅 (응답 완료).

흐름 (ReAct 루프)
──────────────────
  __start__
      └─▶ llm_node
              ├─ (tool_calls 있음) ──▶ tools ──▶ llm_node  (루프백)
              └─ (tool_calls 없음) ──▶ END

수동 ReAct(06_agents.py) vs ToolNode 방식
──────────────────────────────────────────
  06_agents.py  → LangChain AgentExecutor, ReAct 프롬프트 필요, 불투명한 루프
  이 데모      → LangGraph 그래프 구조 명확, 상태 추적 용이, 확장성 높음
"""
from __future__ import annotations
from typing import Annotated, TypedDict
from rich import print

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.llm_factory import build_chat_model
from app.utils.console import header
from catalog.langgraph._viz import render_graph_mermaid


# ── State 정의 ─────────────────────────────────────────────────────────────
class State(TypedDict):
    # add_messages: 동일 id 업데이트 + 새 메시지 append
    messages: Annotated[list, add_messages]


# ── 툴 정의 ────────────────────────────────────────────────────────────────
@tool
def budget_split(total_budget: int, ratio_pr: float = 0.3, ratio_event: float = 0.5) -> dict:
    """총 예산을 홍보(PR)·행사(Event)·기타(etc) 비율로 분배한다.

    Args:
        total_budget: 총 예산 (원 단위)
        ratio_pr:    홍보 비율 (기본 0.3)
        ratio_event: 행사 비율 (기본 0.5)
    """
    ratio_etc = round(1.0 - ratio_pr - ratio_event, 2)
    return {
        "PR":    int(total_budget * ratio_pr),
        "Event": int(total_budget * ratio_event),
        "Etc":   int(total_budget * ratio_etc),
    }


@tool
def risk_checklist(activity: str) -> list[str]:
    """활동 유형에 따른 리스크 체크리스트를 반환한다.

    Args:
        activity: 활동 유형 설명 (예: "야외 공연", "SNS 캠페인")
    """
    base = ["안전관리(현장 동선/보험)", "개인정보 수집 동의", "저작권·초상권"]
    if "야외" in activity:
        base += ["기상 악화 대비", "공공장소 사용 허가"]
    if "sns" in activity.lower() or "소셜" in activity:
        base += ["사전 심의 여부 확인", "댓글 모니터링 계획"]
    return base


# ── 그래프 구성 ────────────────────────────────────────────────────────────
def build_app(llm):
    tools = [budget_split, risk_checklist]
    llm_with_tools = llm.bind_tools(tools)

    def llm_node(state: State) -> dict:
        """LLM 호출 — tool_calls 가 있으면 ToolNode 로, 없으면 END 로."""
        resp = llm_with_tools.invoke(state["messages"])
        return {"messages": [resp]}

    g = StateGraph(State)
    g.add_node("llm", llm_node)
    g.add_node("tools", ToolNode(tools))

    g.set_entry_point("llm")
    # tools_condition: tool_calls 有 → "tools", 無 → END
    g.add_conditional_edges("llm", tools_condition)
    # 툴 실행 후 다시 llm 으로 (ReAct 루프)
    g.add_edge("tools", "llm")

    return g.compile()


def main():
    header("LANGGRAPH 11 — ToolNode + add_messages (ReAct 루프)")
    llm = build_chat_model(temperature=0)

    app = build_app(llm)
    render_graph_mermaid(app, "11_tool_node_graph")

    question = (
        "예산 5천만원으로 야외 전시 오프닝 캠페인을 준비하려고 해. "
        "예산을 홍보 30%, 행사 50%, 기타 20% 로 분배하고, "
        "야외 활동 리스크 체크리스트도 만들어줘."
    )

    print(f"\n[bold]질문:[/bold] {question}\n")
    out = app.invoke({"messages": [HumanMessage(content=question)]})

    # 메시지 스트림 출력 (타입별 구분)
    print("[bold]메시지 흐름[/bold]")
    for msg in out["messages"]:
        role = getattr(msg, "type", type(msg).__name__)
        content = getattr(msg, "content", str(msg))
        if role == "human":
            print(f"  [blue]Human[/blue]: {content[:80]!r}")
        elif role == "ai":
            tc = getattr(msg, "tool_calls", [])
            if tc:
                print(f"  [yellow]AI[/yellow]: tool_calls={[t['name'] for t in tc]}")
            else:
                print(f"  [yellow]AI[/yellow]: {content[:120]!r}")
        elif role == "tool":
            print(f"  [green]Tool[/green]: {content[:120]!r}")

    print("\n[bold]최종 AI 응답[/bold]")
    final_ai = next(
        (m for m in reversed(out["messages"]) if getattr(m, "type", "") == "ai"),
        None,
    )
    if final_ai:
        print(getattr(final_ai, "content", ""))

    print("\n[green]ToolNode 데모 완료[/green]")


if __name__ == "__main__":
    main()
