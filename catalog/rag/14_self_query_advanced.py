"""RAG 14 — Self-Query 고급 (enable_limit / fallback / debug / + Compression)

Self-Query Retriever 작동 흐름
───────────────────────────────
  ① LLM이 자연어 질문을 StructuredQuery (query + filter) 로 변환
       예) "2026년 policy 문서에서 개인정보 내용 3개만"
       → query="개인정보", filter={"year": 2026, "type": "policy"}, limit=3
  ② QueryTranslator(ChromaTranslator 등)가 filter 를 VectorStore 고유 형식으로 변환
  ③ VectorStore가 metadata 필터 + 임베딩 검색 수행

이 데모에서 배우는 것
───────────────────────
  ① enable_limit  : "3개만 줘" 같은 자연어 개수 제한을 LLM이 파싱해 k 로 반영
  ② verbose=True  : LLM이 생성한 StructuredQuery 를 콘솔에 출력 (디버깅 필수)
  ③ fallback      : 메타데이터 조건이 없는 질문 → 순수 semantic 검색으로 자동 폴백
  ④ + Compression : Self-Query 결과를 ContextualCompression 으로 추가 정제
  ⑤ AttributeInfo : type/integer/float/list 다양한 메타데이터 타입 예시

디버깅 팁
─────────
  - verbose=True 로 실행해 filter 가 정상 파싱되는지 먼저 확인
  - LLM 모델이 StructuredQuery 를 제대로 못 만들면 fallback(필터 없는 검색) 발생
  - lark 패키지가 없으면 파서 오류 발생 (requirements.txt 에 lark 필요)
"""
from __future__ import annotations
from rich import print

from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core import settings
from app.core.llm_factory import build_chat_model, build_embeddings
from app.core.rag_utils import load_documents
from app.utils.console import header

COLL = "catalog_self_query_adv"

# ── 메타데이터 스키마 정의 ─────────────────────────────────────────────────
# type 에는 선택지를 description 에 열거 → LLM 파싱 정확도 향상
# AttributeInfo 타입 목록: "string" | "integer" | "float" | "list" | "date"
_METADATA_FIELD_INFO = [
    AttributeInfo(
        name="type",
        description="문서 유형. 가능한 값: policy, pr, proposal, general",
        type="string",
    ),
    AttributeInfo(
        name="year",
        description="문서 작성 연도(정수). 예: 2025, 2026",
        type="integer",
    ),
    AttributeInfo(
        name="org",
        description="기관 식별자 문자열. 예: local-arts-foundation, museum-org",
        type="string",
    ),
]
_DOC_CONTENTS = "문화예술기관의 문서/가이드/제안서 내용"


def _enrich(doc):
    """파일명 기반으로 metadata 추정 (학습용)."""
    src = (doc.metadata or {}).get("source", "") or ""
    lower = src.lower()
    t = (
        "policy"   if any(k in lower for k in ["policy", "규정", "개인정보", "privacy"])
        else "pr"       if any(k in lower for k in ["press", "pr", "보도", "release"])
        else "proposal" if any(k in lower for k in ["proposal", "후원", "제안", "sponsor"])
        else "general"
    )
    doc.metadata = {
        **(doc.metadata or {}),
        "type": t,
        "year": 2026,
        "org": "local-arts-foundation",
    }
    return doc


def _build_vs() -> Chroma:
    docs = list(map(_enrich, load_documents(settings.DOCS_DIR)))
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(docs)
    vs = Chroma(
        persist_directory=settings.CHROMA_PERSIST_DIR,
        embedding_function=build_embeddings(),
        collection_name=COLL,
    )
    vs.add_documents(chunks)
    vs.persist()
    return vs, len(docs)


def main():
    header("RAG 14 — Self-Query 고급")

    vs, n_docs = _build_vs()
    if n_docs == 0:
        print("[yellow]data/docs에 문서를 넣어주세요.[/yellow]")
        return

    llm = build_chat_model(temperature=0)

    # ─────────────────────────────────────────────────────────────────
    # ① enable_limit  +  ② verbose=True
    # ─────────────────────────────────────────────────────────────────
    print("\n[bold cyan]① enable_limit + ② verbose(StructuredQuery 출력)[/bold cyan]")
    print("  verbose=True → 콘솔에 생성된 query/filter 가 출력됩니다.")
    ret_limit = SelfQueryRetriever.from_llm(
        llm=llm,
        vectorstore=vs,
        document_contents=_DOC_CONTENTS,
        metadata_field_info=_METADATA_FIELD_INFO,
        enable_limit=True,     # "N개만" 같은 자연어 수량 제한 파싱
        search_kwargs={"k": 4},  # LLM 이 limit 파싱 실패 시 fallback k
        verbose=True,
    )
    q_limit = "policy 문서에서 2개만 뽑아 개인정보 수집 동의 관련 내용을 알려줘."
    print(f"\n  질문: {q_limit!r}")
    hits_limit = ret_limit.get_relevant_documents(q_limit)
    print(f"  → hits={len(hits_limit)}")
    for i, d in enumerate(hits_limit, 1):
        print(f"    [{i}] type={d.metadata.get('type')}  {d.page_content[:80]!r}")

    # ─────────────────────────────────────────────────────────────────
    # ③ fallback  (메타데이터 조건 없는 질문 → semantic 검색으로 자동 폴백)
    # ─────────────────────────────────────────────────────────────────
    print("\n[bold cyan]③ fallback (메타데이터 조건 없는 질문)[/bold cyan]")
    print("  LLM 이 filter 를 추출하지 못하면 query 만으로 임베딩 검색을 수행합니다.")
    ret_plain = SelfQueryRetriever.from_llm(
        llm=llm,
        vectorstore=vs,
        document_contents=_DOC_CONTENTS,
        metadata_field_info=_METADATA_FIELD_INFO,
        search_kwargs={"k": 3},
        verbose=True,
    )
    q_plain = "관객개발 KPI 설계 방법을 알려줘."   # 메타 조건 없음 → fallback
    print(f"\n  질문: {q_plain!r}")
    hits_plain = ret_plain.get_relevant_documents(q_plain)
    print(f"  → fallback hits={len(hits_plain)}")
    for i, d in enumerate(hits_plain, 1):
        print(f"    [{i}] meta={d.metadata}  {d.page_content[:80]!r}")

    # ─────────────────────────────────────────────────────────────────
    # ④ Self-Query + ContextualCompression 결합
    # ─────────────────────────────────────────────────────────────────
    print("\n[bold cyan]④ Self-Query + ContextualCompression 결합[/bold cyan]")
    print(
        "  Self-Query 로 메타 필터링 → Compression 으로 관련 구절만 추출\n"
        "  두 단계를 거쳐 Context 길이를 줄이고 Hallucination 위험 감소"
    )
    compressor = LLMChainExtractor.from_llm(llm)
    cc_ret = ContextualCompressionRetriever(
        base_retriever=ret_plain,
        base_compressor=compressor,
    )
    q_cc = "2026년 관객개발 캠페인 성과를 측정하는 KPI 기준을 알려줘."
    print(f"\n  질문: {q_cc!r}")
    cc_hits = cc_ret.get_relevant_documents(q_cc)
    print(f"  → compressed hits={len(cc_hits)}")
    for i, d in enumerate(cc_hits, 1):
        print(f"    [{i}] {d.page_content[:200]!r}")

    # ─────────────────────────────────────────────────────────────────
    # ⑤ 다양한 AttributeInfo 타입 예시 (참고용, 실행 없음)
    # ─────────────────────────────────────────────────────────────────
    print("\n[bold cyan]⑤ AttributeInfo 타입 예시 (참고)[/bold cyan]")
    examples = [
        ('string',  'type',      '"policy|pr|proposal|general" 같은 열거형'),
        ('integer', 'year',      '연도, 페이지 수 등 정수'),
        ('float',   'relevance', '관련도 점수 (0.0 ~ 1.0)'),
        ('list',    'tags',      '["홍보","후원","KPI"] 같은 복수 태그'),
        ('date',    'created',   '"2026-06-01" ISO 날짜 문자열'),
    ]
    for t, name, desc in examples:
        print(f"  AttributeInfo(name={name!r}, type={t!r}) — {desc}")

    print("\n[green]Self-Query 고급 데모 완료[/green]")


if __name__ == "__main__":
    main()
