# Self-Query Retriever 심화 노트

## 개요

Self-Query Retriever 는 자연어 질문에서 **메타데이터 조건(filter)** 을  
LLM 이 자동으로 추출해 VectorStore 의 구조화 검색으로 연결합니다.

```
"2026년 policy 문서에서 개인정보 내용 3개만 찾아줘"
         ↓  LLM 파싱
query  = "개인정보"
filter = {year: 2026, type: "policy"}
limit  = 3
         ↓  Translator
Chroma WHERE year=2026 AND type="policy" + 임베딩 검색
```

---

## 준비 조건 (3가지 모두 필요)

1. **문서에 의미 있는 metadata 가 저장돼 있어야 함**
   - type, year, org 등 — 파일명·본문 파싱으로 자동화 가능
   - `infer_metadata_from_filename()` 패턴 참고 (`app/core/rag_utils.py`)

2. **VectorStore 가 metadata 필터를 지원해야 함**
   - Chroma: 지원 ✅ (ChromaTranslator 내장)
   - FAISS: 미지원 ❌ (Self-Query 와 직접 연동 불가)
   - Pinecone, Weaviate, Qdrant 등: 지원 ✅

3. **LLM 이 StructuredQuery 를 안정적으로 생성해야 함**
   - `verbose=True` 로 생성된 쿼리를 먼저 확인하세요
   - 모델 성능에 따라 fallback(필터 없는 검색) 발생 가능
   - `lark` 패키지 필수 (`requirements.txt` 확인)

---

## AttributeInfo 타입 & 설계 팁

```python
from langchain_classic.chains.query_constructor.schema import AttributeInfo

AttributeInfo(name="type",      description="policy|pr|proposal|general",    type="string")
AttributeInfo(name="year",      description="문서 연도 정수. 예: 2026",         type="integer")
AttributeInfo(name="org",       description="기관 식별자 문자열",               type="string")
AttributeInfo(name="relevance", description="관련도 점수 0.0~1.0",             type="float")
AttributeInfo(name="tags",      description='태그 리스트. 예: ["홍보","후원"]', type="list")
```

**description 에 가능한 값을 열거**하면 LLM 파싱 정확도가 높아집니다.

---

## 주요 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `enable_limit` | `False` | `True` 로 설정하면 "3개만" 같은 자연어 수량 제한을 파싱 |
| `verbose` | `False` | `True` 로 설정하면 생성된 StructuredQuery 를 콘솔 출력 |
| `search_kwargs` | `{"k": 4}` | fallback k (LLM 이 limit 파싱 실패 시 사용) |

---

## fallback 동작

LLM 이 filter 를 추출하지 못하는 경우 (조건 없는 일반 질문):
- 자동으로 **순수 semantic 검색** (filter 없이 임베딩 검색)
- 결과가 예상보다 넓게 나올 수 있음
- `verbose=True` 로 filter 가 생성됐는지 먼저 확인

---

## 권장 디버깅 순서

```
1. verbose=True 로 StructuredQuery 확인
       → query / filter / limit 이 올바른가?

2. metadata 를 직접 조회해 필드 값 확인
       vs.get(where={"type": "policy"})

3. LLM 변경 (파싱 능력 모델 의존도 높음)
       temperature=0 필수

4. description 수정 → 선택지 명확히 열거

5. lark 패키지 설치 여부 확인
```

---

## Self-Query + Compression 결합 패턴

```python
# Self-Query → 메타 필터로 후보 좁히기
self_q_ret = SelfQueryRetriever.from_llm(...)

# Compression → 관련 구절만 추출해 Context 압축
compressor = LLMChainExtractor.from_llm(llm)
final_ret = ContextualCompressionRetriever(
    base_retriever=self_q_ret,
    base_compressor=compressor,
)
```

→ 실행 가능한 예시: `catalog/rag/14_self_query_advanced.py` ④번

---

## 데모 파일 목록

| 파일 | 내용 |
|------|------|
| `11_self_query_retriever.py` | 기본 동작 — metadata 부착 + SelfQueryRetriever |
| `14_self_query_advanced.py` | 고급 — enable_limit / verbose / fallback / +Compression |
| `app/server/self_query_api.py` | FastAPI 엔드포인트 연동 (`POST /rag/self-query`) |
