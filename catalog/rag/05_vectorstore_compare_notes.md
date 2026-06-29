# VectorStore / Retriever 비교 노트

## VectorStore vs Retriever

| 구분 | 역할 | 예시 |
|------|------|------|
| **VectorStore** | 임베딩 저장·검색 엔진 | Chroma, FAISS, Pinecone |
| **Retriever**   | 어떤 전략으로 문서를 꺼낼지 | TopK, MMR, MultiQuery, Compression |

VectorStore 는 창고, Retriever 는 창고에서 물건을 꺼내는 방법입니다.  
`.as_retriever()` 한 줄로 VectorStore → Retriever 로 변환됩니다.

---

## 이 레포에서 다루는 VectorStore

### Chroma (`catalog/rag/03_vectorstore_chroma.py`)
- 영속 DB(SQLite 기반 로컬 파일 저장)
- metadata 필터 지원 → Self-Query Retriever 연동 최적
- 소규모~중규모(수십만 벡터) 실용적
- 컬렉션 단위 관리, 재시작 후에도 데이터 유지

### FAISS (`catalog/rag/08_vectorstore_faiss.py`, `13_faiss_advanced.py`)
- 메타데이터 필터 미지원 (순수 벡터 검색)
- 인메모리 동작 → 빠른 실험·배치 파이프라인에 유리
- `save_local / load_local` 로 직렬화 저장
- `merge_from` 으로 여러 인덱스 합치기 가능
- 수백만 벡터 이상: IVF/HNSW 인덱스로 확장 가능

#### FAISS 인덱스 타입 (심화)
| 타입 | 특징 | 적합 규모 |
|------|------|----------|
| **IndexFlatL2** | 전수비교 L2(기본값), 정확하지만 O(n) | 수만 이하 |
| **IndexIVFFlat** | 클러스터링으로 탐색 범위 축소 | 수십만~수백만 |
| **HNSW** | 그래프 기반 ANN, 빠른 속도+높은 정확도 | 수십만+ |

> LangChain `FAISS.from_documents()` 의 기본 타입은 `IndexFlatL2`.  
> 대규모 운영에서는 faiss 라이브러리를 직접 써서 인덱스 타입을 교체한다.

---

## Retriever 전략 비교

| 전략 | 파일 | 특징 |
|------|------|------|
| **TopK** | 기본값 | 단순 유사도 상위 k개, 중복·편향 가능 |
| **MMR** | `06_retriever_mmr.py` | 다양성+유사도 절충, 중복 감소 |
| **MultiQuery** | `04_multiquery_compression.py` | 질문을 여러 관점으로 재작성 → Recall 향상 |
| **Compression** | `04_multiquery_compression.py` | 가져온 문서에서 관련 구절만 추출 → Context 압축 |
| **BM25** | `09_retriever_bm25.py` | 키워드 기반, 고유명사·약어에 강함 |
| **Ensemble** | `10_ensemble_retriever.py` | BM25 + Vector 결합, 가중치 조정 |
| **Self-Query** | `11_self_query_retriever.py` | LLM 이 질문에서 메타 필터 추출 |
| **score_threshold** | `13_faiss_advanced.py` ③ | 유사도 임계값 미만 문서 제외 |

---

## Chroma vs FAISS 선택 가이드

```
metadata 필터 필요?   → Chroma
영속 DB 필요?         → Chroma
실험·배치·고속?       → FAISS
인덱스 merge 필요?    → FAISS
수백만+ 벡터?         → FAISS (IVF/HNSW)
Self-Query 연동?      → Chroma (Chroma 전용 Translator 지원)
```

---

## 실전 파이프라인 조합 예시

```
문서 로드 → 청크 분할
    ↓
FAISS (고속 실험)  or  Chroma (운영 영속)
    ↓
retriever = vs.as_retriever(search_type="mmr")
    ↓
EnsembleRetriever([bm25, vector], weights=[0.4, 0.6])
    ↓
ContextualCompressionRetriever  (관련 구절만 추출)
    ↓
LLM + RAG 프롬프트
```
