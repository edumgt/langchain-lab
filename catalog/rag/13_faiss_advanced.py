"""RAG 13 — FAISS 고급 (score / MMR / add / merge / retriever 모드)

FAISS 내부 동작 메모
──────────────────
• 기본(IndexFlatL2): 전수비교 L2 거리. 정확하지만 O(n). 수만 벡터까지 실용적.
• IVF(Inverted File Index): 클러스터링으로 탐색 범위를 줄임. 수백만+ 벡터 대응.
• HNSW: 그래프 기반 ANN. 높은 정확도 + 빠른 속도. 메모리 사용량 큰 편.
• faiss-cpu 기본 타입은 IndexFlatL2 (LangChain FAISS.from_documents 사용 시).

이 데모에서 배우는 것
──────────────────────
  ① similarity_search_with_score  : L2 거리(낮을수록 유사)와 함께 반환
  ② max_marginal_relevance_search : 다양성+유사도를 동시에 고려하는 MMR 검색
  ③ as_retriever 세 가지 모드     : similarity / mmr / similarity_score_threshold
  ④ add_documents                 : 기존 인덱스에 문서 추가(점진적 인덱싱)
  ⑤ merge_from                   : 두 FAISS 인덱스를 하나로 병합
  ⑥ save_local / load_local       : 직렬화 저장·복원

Chroma vs FAISS 선택 기준 (간단 요약)
────────────────────────────────────
  Chroma   → 영속 DB, metadata 필터 지원, Self-Query 연동 용이, 소규모~중규모
  FAISS    → 메모리 내 고속, 학습/실험/배치 파이프라인, merge 기능, 수백만 벡터 대응
"""
from __future__ import annotations
import os
from rich import print
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core import settings
from app.core.llm_factory import build_embeddings
from app.core.rag_utils import load_documents
from app.utils.console import header

FAISS_DIR_MERGED = "/app/storage/faiss_adv_merged"

QUERY = "후원 패키지 구성 요소와 기업 혜택"


def main():
    header("RAG 13 — FAISS 고급")

    docs = load_documents(settings.DOCS_DIR)
    if not docs:
        print("[yellow]data/docs에 문서를 넣어주세요.[/yellow]")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(docs)
    emb = build_embeddings()

    # 학습을 위해 문서를 두 파트로 나눠 별도 인덱스 구성
    half = max(1, len(chunks) // 2)
    vs_a = FAISS.from_documents(chunks[:half], emb)
    vs_b = FAISS.from_documents(chunks[half:], emb)
    print(f"vs_a 벡터 수: {vs_a.index.ntotal}, vs_b 벡터 수: {vs_b.index.ntotal}")

    # ─────────────────────────────────────────────────────────────────
    # ① similarity_search_with_score  (L2 거리 확인)
    # ─────────────────────────────────────────────────────────────────
    print("\n[bold cyan]① similarity_search_with_score[/bold cyan]")
    print("  L2 거리는 낮을수록 쿼리와 유사. Chroma의 cosine score와 방향이 반대임에 주의.")
    results_with_score = vs_a.similarity_search_with_score(QUERY, k=3)
    for doc, score in results_with_score:
        print(f"  score(L2↓)={score:.4f}  {doc.page_content[:80]!r}")

    # ─────────────────────────────────────────────────────────────────
    # ② max_marginal_relevance_search  (MMR)
    # ─────────────────────────────────────────────────────────────────
    print("\n[bold cyan]② max_marginal_relevance_search (MMR)[/bold cyan]")
    print(
        "  lambda_mult=1.0 → 순수 유사도(TopK와 동일)\n"
        "  lambda_mult=0.0 → 최대 다양성(내용 중복 최소화)\n"
        "  lambda_mult=0.5 → 절충 (권장 시작값)"
    )
    mmr_hits = vs_a.max_marginal_relevance_search(
        QUERY,
        k=3,
        fetch_k=20,      # 후보 N개를 먼저 뽑고 MMR로 k개 선택
        lambda_mult=0.5,
    )
    for i, d in enumerate(mmr_hits, 1):
        print(f"  mmr hit {i}: {d.page_content[:100]!r}")

    # ─────────────────────────────────────────────────────────────────
    # ③ as_retriever 세 가지 모드
    # ─────────────────────────────────────────────────────────────────
    print("\n[bold cyan]③ as_retriever 모드 비교[/bold cyan]")

    ret_topk = vs_a.as_retriever(search_kwargs={"k": 3})

    ret_mmr = vs_a.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 3, "fetch_k": 15, "lambda_mult": 0.6},
    )

    # score_threshold: L2 거리가 threshold 이하인 문서만 반환
    # (FAISS L2는 낮을수록 유사 → threshold는 "최대 허용 L2 거리")
    ret_thresh = vs_a.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"score_threshold": 1.2, "k": 5},
    )

    q = "관객개발 캠페인 KPI"
    for name, ret in [("topk", ret_topk), ("mmr", ret_mmr), ("threshold", ret_thresh)]:
        hits = ret.get_relevant_documents(q)
        print(f"  [{name:10s}] hits={len(hits)}")

    # ─────────────────────────────────────────────────────────────────
    # ④ add_documents  (점진적 추가)
    # ─────────────────────────────────────────────────────────────────
    print("\n[bold cyan]④ add_documents (기존 인덱스에 청크 추가)[/bold cyan]")
    before = vs_a.index.ntotal
    vs_a.add_documents(chunks[half : half + min(5, len(chunks) - half)])
    after = vs_a.index.ntotal
    print(f"  추가 전={before}, 추가 후={after} (delta={after - before})")

    # ─────────────────────────────────────────────────────────────────
    # ⑤ merge_from  (두 인덱스 합치기)
    # ─────────────────────────────────────────────────────────────────
    print("\n[bold cyan]⑤ merge_from (vs_a ← vs_b 병합)[/bold cyan]")
    before_merge = vs_a.index.ntotal
    vs_a.merge_from(vs_b)
    print(f"  병합 전={before_merge}, 병합 후={vs_a.index.ntotal}")
    print("  활용: 부서별/날짜별로 별도 인덱싱 후 서비스 시점에 하나로 합치는 패턴에 유용")

    # ─────────────────────────────────────────────────────────────────
    # ⑥ save_local / load_local
    # ─────────────────────────────────────────────────────────────────
    print("\n[bold cyan]⑥ save_local / load_local[/bold cyan]")
    os.makedirs(FAISS_DIR_MERGED, exist_ok=True)
    vs_a.save_local(FAISS_DIR_MERGED)
    vs_loaded = FAISS.load_local(
        FAISS_DIR_MERGED, emb, allow_dangerous_deserialization=True
    )
    print(f"  저장 후 로드 벡터 수: {vs_loaded.index.ntotal}")
    print("  주의: allow_dangerous_deserialization=True 는 신뢰할 수 있는 파일에만 사용")

    # 최종 검색 확인
    final_hits = vs_loaded.similarity_search(QUERY, k=2)
    print(f"\n[green]최종 로드된 인덱스 검색 결과 {len(final_hits)}건[/green]")
    for i, d in enumerate(final_hits, 1):
        print(f"  [{i}] {d.page_content[:120]!r}")

    print("\n[green]FAISS 고급 데모 완료[/green]")


if __name__ == "__main__":
    main()
