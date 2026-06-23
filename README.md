<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css" />

# LangChain Catalog Lab (Docker + Python)
  
LangChain의 기능을 **“카탈로그(기능별 독립 데모)”** 형태로 최대한 촘촘하게 정리한 학습 레포입니다.  
각 데모는 **단독 실행 가능**하며, 동일한 `LLM Factory`를 통해 **Ollama / OpenAI-호환 / OpenAI**를 스위칭할 수 있습니다.

- <i class="fa-solid fa-circle-check"></i> Docker 한 번으로 실행
- <i class="fa-solid fa-circle-check"></i> LCEL(Runnable) 중심 (LangChain의 “조합 언어”)
- <i class="fa-solid fa-circle-check"></i> Prompts / Output Parsers / Structured Output / Streaming
- <i class="fa-solid fa-circle-check"></i> Tools / Tool calling / Agents (ReAct 등)
- <i class="fa-solid fa-circle-check"></i> Retrievers / VectorStores / Loaders / RAG 고급 패턴
- <i class="fa-solid fa-circle-check"></i> Memory / History / Summarization / Windowing
- <i class="fa-solid fa-circle-check"></i> Router / Multi-prompt / JSON mode / Guardrails (실습 관점)
- <i class="fa-solid fa-circle-check"></i> SQL / CSV / Web 요청(안전한 범위) 유틸
- <i class="fa-solid fa-circle-check"></i> Callbacks / Tracing (옵션 LangSmith)
- <i class="fa-solid fa-circle-check"></i> Eval (미니) + 회귀 테스트 샘플

> <i class="fa-solid fa-triangle-exclamation"></i>️ 일부 기능은 모델 백엔드(예: Ollama vs OpenAI-호환)에 따라 “지원 방식/결과”가 다릅니다.  
> 각 데모 파일 상단에 호환성 노트를 적어두었습니다.

---

## 0) 실행

```bash
cp .env.example .env
docker compose up --build
```
---
```
docker compose down -v
docker compose build --no-cache
docker compose up
```

---
![alt text](image.png)

---

개별 데모 실행:

```bash
docker compose run --rm lab python catalog/prompts/01_prompt_templates.py
docker compose run --rm lab python catalog/lcel/03_parallel_and_assign.py
docker compose run --rm lab python catalog/tools/02_tool_calling_bind_tools.py
docker compose run --rm lab python catalog/rag/04_multiquery_compression.py
```

또는 `make demo`:

```bash
make demo D=catalog/agents/02_react_agent.py
```

---

## 1) LLM 연결 (기존 Docker LLM 우선)

### Ollama(권장) — EXAONE 포함
```env
LLM_PROVIDER=auto
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=exaone3.5:2.4b   # 기본값: LG AI 연구원 EXAONE 3.5 (경량)
# OLLAMA_MODEL=exaone3.5:7.8b  # 더 강력한 버전
# OLLAMA_MODEL=llama3.1:8b     # 기존 llama 모델로 전환 시
OLLAMA_EMBED_MODEL=nomic-embed-text
```

> **EXAONE 모델 최초 실행 전 1회 pull 필요:**
> ```bash
> ollama pull exaone3.5:2.4b   # ~1.5GB
> ollama pull exaone3.5:7.8b   # ~5GB (선택)
> ```

### OpenAI-호환 (LM Studio / vLLM 등)
```env
LLM_PROVIDER=openai_compatible
OPENAI_COMPAT_BASE_URL=http://host.docker.internal:1234/v1
OPENAI_COMPAT_API_KEY=lm-studio
OPENAI_COMPAT_MODEL=gpt-4o-mini
```

### OpenAI
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=YOUR_KEY
OPENAI_MODEL=gpt-4o-mini
```

---

## 2) 카탈로그 인덱스

- `catalog/prompts/*` : PromptTemplate / ChatPromptTemplate / Few-shot / Partial / Messages
- `catalog/lcel/*` : RunnableLambda / Passthrough / Parallel / Assign / Retry / Fallback / Batch / Stream
- `catalog/output/*` : StrOutputParser / JsonOutputParser / PydanticOutputParser / FixingParser
- `catalog/structured/*` : with_structured_output (Pydantic) / list schema / strict json
- `catalog/memory/*` : File history / window memory / summarization memory
- `catalog/tools/*` : @tool / bind_tools / tool schemas / tool-result patterns
- `catalog/agents/*` : ReAct agent / tool agent / 안전한 설계 팁
- `catalog/rag/*` : loaders / splitters / vectorstores / retrievers / RAG patterns
- `catalog/routers/*` : route classification / multi-prompt routing / conditional chains
- `catalog/sql/*` : create_sql_query_chain / SQLite example / 결과 요약
- `catalog/callbacks/*` : callback handler / timing / logging / tracing flags
- `catalog/eval/*` : mini judge / regression set runner
- `data/docs/*` : RAG 데모용 문서 위치
- `storage/*` : 벡터DB / chat history / 샘플 DB

---

## 3) 추천 학습 순서(카탈로그형)

1) prompts → 2) lcel → 3) output/structured → 4) tools → 5) agents → 6) rag → 7) routers → 8) memory → 9) sql → 10) callbacks/eval

---

## 4) v2 추가 카탈로그 (확장팩)

### LangGraph (워크플로우/상태 머신)
- `catalog/langgraph/01_minimal_graph.py`
- `catalog/langgraph/02_agentic_loop_graph.py`
- `catalog/langgraph/03_guarded_graph.py`

> 참고: LangGraph 카탈로그는 실행 시 mermaid 그래프를 콘솔에 출력하고,
> `.mmd` 파일을 `/app/storage/langgraph/` 아래에 저장합니다.

### VectorStore / Retriever 비교
- `catalog/rag/05_vectorstore_compare_notes.md`
- `catalog/rag/06_retriever_mmr.py`
- `catalog/rag/07_self_query_retriever_note.md` *(백엔드/메타데이터 설계에 따라 적용)*

### Guardrails 패턴(실습 관점)
- `catalog/guardrails/01_schema_guard.py`
- `catalog/guardrails/02_context_only_rag_guard.py`
- `catalog/guardrails/03_policy_checks.py`

### Caching / Tool Result 패턴
- `catalog/perf/01_llm_cache_sqlite.py`
- `catalog/tools/03_tool_result_patterns.py`

> 주의: 일부 데모는 설치/환경에 따라 선택적으로 동작하도록 설계되어 있습니다(설명 포함).

---

## 5) v3 추가 카탈로그 (FAISS/자기질의/고급 LangGraph)

### RAG 확장: FAISS / BM25 / Ensemble / Self-Query
- `catalog/rag/08_vectorstore_faiss.py`
- `catalog/rag/09_retriever_bm25.py`
- `catalog/rag/10_ensemble_retriever.py`
- `catalog/rag/11_self_query_retriever.py`

### LangGraph 확장: Checkpoint / Subgraph / Multi-role synthesis
- `catalog/langgraph/04_checkpoint_sqlite.py`
- `catalog/langgraph/05_subgraph_pattern.py`
- `catalog/langgraph/06_multi_role_agents.py`

### Guardrails 확장: Citation required
- `catalog/guardrails/04_citation_required_guard.py`

### Perf 확장: batch vs single
- `catalog/perf/02_batch_vs_single.py`

---

## 6) v4 추가 카탈로그 (안전한 에이전트/툴 + RAG 회귀평가)

### Safe Agent 패턴(라우터→툴 실행→검증→최종 응답)
- `catalog/agents/03_safe_tool_router.py`

### Tool 결과 검증(스키마)
- `catalog/tools/04_tool_result_validator.py`

### LangGraph HITL 승인 패턴(비대화형 환경 지원)
- `catalog/langgraph/07_hitl_approval.py`
  - `.env`에서 `AUTO_APPROVE`, `APPROVE_TOKEN`로 승인 흐름 실습

### RAG 회귀평가 자동화(golden set)
- `data/eval/golden.jsonl`
- `catalog/eval/03_rag_regression.py` → `/app/storage/eval_rag_report.json` 저장

---

## 7) v5 추가 카탈로그 (LLM Judge / 정책 분류기 / 실제 HITL 입력)

### LLM-as-a-Judge 평가(grounding)
- `catalog/eval/04_llm_judge_grounding.py` → `/app/storage/eval_llm_judge_report.json`

### Eval Suite Runner(합본)
- `catalog/eval/05_eval_suite_runner.py` → `/app/storage/eval_suite_report.json`

### LLM 정책 분류기(Structured Classifier)
- `catalog/guardrails/05_policy_classifier_llm.py`

### HITL 실제 입력(터미널 승인 대기)
- `catalog/langgraph/08_hitl_cli_pause.py`
  - TTY 실행 예: `docker compose run --rm -it lab python catalog/langgraph/08_hitl_cli_pause.py`

---

## 8) v6 End-to-End ArtBiz App (FastAPI + HITL + RAG)

이 레포는 카탈로그 데모뿐 아니라, 예술경영전문가 AI를 위한 **엔드투엔드 템플릿 앱**도 포함합니다.

### 실행 (API 서버)
```bash
cp .env.example .env
docker compose up --build api
```

- 웹 UI: `http://localhost:8000/`
- Swagger: `http://localhost:8000/docs`

자세한 설명: `docs/E2E_APP.md`

### CLI 실행
```bash
docker compose run --rm lab python -m app.cli "관객개발 KPI 3개 제안" --mode rag
docker compose run --rm lab python -m app.cli "예산 3천만원 2주 실행계획" --mode plan
```

---

## 9) v7 ArtBiz Domain Tools API

FastAPI에 `/tools/*` 엔드포인트가 추가되었습니다.

- `POST /tools/budget-split`
- `POST /tools/timeline`
- `POST /tools/sponsorship-package`
- `POST /tools/report`

문서: `docs/TOOLS_API.md`

### 실행
```bash
cp .env.example .env
docker compose up --build api
```

---

## 10) v8 Document Upload + Self-Query + Proposal Generator + Tool Eval

### 실행
```bash
cp .env.example .env
docker compose up --build api
```

- 웹 UI: `http://localhost:8000/`
- Swagger: `http://localhost:8000/docs`

### 문서 업로드
- `POST /docs/upload` (pdf/md/txt)

### Self-Query RAG
- `POST /rag/self-query`

### 후원 제안서 생성
- `POST /artbiz/proposal`

### 평가(전체)
```bash
docker compose run --rm lab python catalog/eval/05_eval_suite_runner.py
```

자세한 설명: `docs/V8_FEATURES.md`

---

## 10) v9 운영형 확장 (Metadata 추출 / Self-Query 파싱 노출 / Proposal HITL)

- 업로드 메타데이터 추출: `POST /docs/upload`
- Self-Query 파싱/필터 확인: `POST /rag/self-query`
- 후원 제안서 생성(+승인): `POST /artbiz/proposal`

문서: `docs/V9_FEATURES.md`

---

## 11) v10 운영 모드 (Reindex Queue / Proposal 저장(MD/PDF) / Citation Eval)

### 재인덱싱 큐
- `POST /ops/queue-reindex` (mode: full|incremental)
- 워커: `catalog/ops/01_index_worker.py`

### 제안서 저장(버전)
- `/artbiz/proposal`에 `save=true` 옵션
- 목록: `GET /artbiz/proposals`

문서: `docs/V10_FEATURES.md`

---

## 12) v11 (PDF 개선 + Proposal 메타/승인 기록)

- PDF: Markdown 스타일 렌더링(헤딩/리스트/테이블)
- Proposal 버전 메타: tags/template_version/status/approved_by/approved_at
- 승인 시 버전 승인 기록 반영

문서: `docs/V11_FEATURES.md`

---

## 13) v12 (출판 품질 PDF + 한글 폰트 옵션)

- PDF: 커버/목차/헤더·푸터/표 스타일 고정
- 한글 폰트: `assets/fonts/*.ttf` 또는 `.env`(ARTBIZ_FONT_*)로 제공 시 자동 등록

문서: `docs/V12_FEATURES.md`

---

## 14) v13 (고정형 제안서 템플릿 + 자동 정규화 + 구조 Eval)

- 템플릿: `GET /artbiz/proposal/template`
- 구조 체크: `POST /artbiz/proposal/check`
- proposal 생성 기본값: `normalize=true` (10개 섹션/필수 표/근거 섹션 고정)
- Eval: `catalog/eval/08_structure_compliance.py`

문서: `docs/V13_FEATURES.md`

---

## 15) v14 (섹션별 LLM 리라이트 + TOOL_DATA 결정론 매핑 + 일관성 리포트)

- 기본 모드: `rewrite_mode=llm_sections`
- 표/숫자: TOOL_DATA로 코드가 생성(추측 방지)
- 응답: `consistency_report` 포함

문서: `docs/V14_FEATURES.md`

---

## 16) v15 (섹션별 인용 각주 + 인용 위치/빈도 Eval)

- 섹션별 `SOURCE 1/2` 마커 보정(footnote-like)
- 응답: `citation_enforce_report`, `citation_placement_report`
- Eval: `catalog/eval/10_citation_placement.py`

문서: `docs/V15_FEATURES.md`

---

## 17) v16 ([1][2] 각주 + 부록 매핑 + Eval 11)

- 본문: SOURCE 1/2 → [1]/[2]로 통일
- 부록: [1]/[2]에 실제 스니펫 매핑 자동 삽입
- Eval: `catalog/eval/11_footnote_mapping.py`

문서: `docs/V16_FEATURES.md`


---

# '사용자 반응 데이터를 기반으로 에이전트의 추천 로직을 지속적으로 개선'의 의미

이 문장은 쉽게 말해 **"사용자들이 내비친 반응(행동)을 학습해서, AI나 시스템(에이전트)이 다음번에 더 똑똑하고 정확한 추천을 해주도록 계속 업데이트한다"**는 뜻입니다.

기업들이 유튜브, 넷플릭스, 쇼핑 앱 등에서 사용하는 **'개인화 추천 알고리즘의 작동 원리'**를 전문적인 IT 용어로 표현한 문장입니다.

---

## 1. 단어별 상세 의미

* **사용자 반응 데이터**: 사용자가 서비스 내에서 했던 모든 '행동 기록'을 말합니다.
  * *예시*: 특정 상품을 클릭함(클릭), 영상을 끝까지 봄(시청 시간), '좋아요'를 누름, 장바구니에 담음, 혹은 그냥 빠르게 넘겨버림(무시) 등.
* **에이전트 (Agent)**: 여기서는 추천을 담당하는 **'AI 프로그램'** 또는 **'추천 시스템'**을 뜻합니다.
* **추천 로직 (Logic)**: AI가 무엇을 추천할지 결정하는 **'기준과 공식(알고리즘)'**입니다.
  * *예시*: "A를 본 사람은 B도 좋아할 확률이 80%다"라는 내부적인 계산 방식.
* **지속적으로 개선**: 일회성으로 끝나는 게 아니라, 데이터가 쌓일 때마다 실시간 또는 주기적으로 공식을 수정하고 발전시킨다는 뜻입니다.

---

## 2. 한눈에 보는 작동 흐름 (선순환 구조)

1. **추천**: AI(에이전트)가 사용자에게 상품이나 콘텐츠를 보여줍니다.
2. **반응**: 사용자가 그걸 클릭하거나(긍정) 그냥 지나칩니다(부정). $
ightarrow$ **[사용자 반응 데이터 생성]**
3. **학습**: AI가 이 데이터를 분석합니다. (*"아, 이런 취향의 사람은 이걸 싫어하는구나?"*)
4. **개선**: 추천 공식을 수정합니다. $
ightarrow$ **[추천 로직 개선]**
5. **결과**: 다음번에 사용자가 앱에 접속했을 때, 훨씬 더 마음에 드는 상품을 딱 맞춰 보여주게 됩니다.

---

> <i class="fa-solid fa-lightbulb"></i> **한 줄 요약**
> 사용자가 쓰면 쓸수록 데이터가 쌓이고, 그 데이터 덕분에 AI가 점점 더 내 입맛에 맞는 걸 기가 막히게 추천하도록 진화한다는 뜻입니다.

---

# Langfuse를 통한 LLM 모니터링 및 실무 연동 가이드

## 1. Langfuse란 무엇인가?

**Langfuse(랭퓨즈)**는 LLM(거대 언어 모델) 기반 서비스의 개발, 구동, 최적화 전 과정을 추적하고 관리할 수 있도록 돕는 **오픈소스 LLM 모니터링 및 Observability(관측 가능성) 플랫폼**입니다. 

일반적인 웹 서비스에서 시스템의 상태를 모니터링하기 위해 Datadog이나 구글 애널리틱스를 사용하는 것처럼, LLM 애플리케이션의 성능, 비용, 프롬프트 품질을 전문적으로 관리하기 위해 사용됩니다.

### <i class="fa-solid fa-lightbulb"></i> 핵심 제공 기능 4가지
1. **Tracing (실행 과정 추적):** 사용자의 요청이 들어와 답변이 나갈 때까지 내부에서 일어나는 모든 단계(RAG, 프롬프트 조립, API 호출 등)를 타임라인 형태로 시각화하여 어떤 구간에서 병목(지연)이 발생하는지 파악합니다.
2. **Cost Tracking (비용 및 토큰 추적):** 모델별(GPT, Claude 등) 입력/출력 토큰 수를 실시간으로 집계하고, 이를 실제 청구 비용(USD)으로 계산하여 대시보드에 표시합니다.
3. **Prompt Management (프롬프트 관리):** 소스 코드 내부에 프롬프트를 하드코딩하지 않고, Langfuse 서버에서 버전별로 중앙 관리하며 코드 배포 없이 실시간으로 프롬프트를 교체 및 테스트할 수 있습니다.
4. **Evaluation (답변 품질 평가):** AI 답변에 대한 유저 피드백(좋아요/싫어요)을 수집하거나, 다른 LLM을 활용해 환각 현상(Hallucination) 유무, 답변의 적절성 등을 자동 평가합니다.

---

## 2. Python 환경에서의 실무 연동 방법

Langfuse는 기존 OpenAI, LangChain 등 주요 라이브러리와의 유기적인 연동을 지원합니다. 코드 내에 전용 데코레이터(`@observe()`)를 붙이는 것만으로도 복잡한 로그를 손쉽게 수집할 수 있습니다.

### 2.1 사전 준비 및 라이브러리 설치

터미널에서 필요한 패키지를 설치하고, Langfuse 대시보드에서 발급받은 API 키를 환경 변수로 등록합니다.

```bash
# 필수 라이브러리 설치
pip install langfuse openai
```

---

# EXAONE — LG AI연구원의 대한민국 대표 거대언어모델(LLM)

## 1. EXAONE이란?

**EXAONE(엑사원)**은 LG AI연구원이 자체 개발한 **대한민국의 대표적인 거대언어모델(LLM)이자 멀티모달(Multimodal) AI 시리즈**입니다.

이름은 **"EXpert AI for EveryONE"(모두를 위한 전문가 AI)**의 줄임말로, 세상의 지식을 지혜로 바꾸어 **누구나 전문가 수준의 능력을 발휘하도록 돕겠다**는 비전을 담고 있습니다.

> 네이버의 HyperCLOVA X와 함께 대한민국을 대표하는 2대 토종 AI 모델 중 하나입니다.

---

## 2. 핵심 특징 및 강점

### 2.1 한국어 · 한국 문화에 압도적인 특화

| 구분 | 내용 |
|------|------|
| **한국어 이해력** | 해외 모델(GPT, Claude 등)이 종종 놓치는 한국어의 미묘한 뉘앙스, 속담, 줄임말, 최신 트렌드 문화를 정확하게 이해 |
| **독자적 토크나이저** | 한국어 텍스트를 AI가 이해하는 최소 단위(토큰)로 쪼갤 때 훨씬 효율적인 독자적 방식 사용 |
| **비용 · 속도** | 외국계 AI 대비 같은 한국어 문장 처리 시 더 적은 토큰 사용 → 빠르고 경제적 |

### 2.2 글과 이미지를 동시에 다루는 멀티모달(Multimodal) AI

EXAONE은 태생부터 텍스트뿐만 아니라 **시각 정보(이미지)를 동시에 처리**하는 데 강점을 두고 개발되었습니다.

- **EXAONE 4.5** 기준: 비전 인코더(눈)와 언어모델(뇌)을 완벽하게 **하나의 구조(Unified Architecture)**로 통합
- 산업 현장의 복잡한 **계약서, 기술 도면, 재무제표, 인포그래픽** 등 텍스트와 이미지가 얽힌 전문 문서를 정확하게 읽고 추론하는 능력이 세계 최고 수준

### 2.3 전문가용 AI — 강력한 논리적 추론(Reasoning)

단순히 그럴듯한 문장을 지어내는 수준을 넘어, **수학 · 코딩 · 과학(STEM) 분야의 논리적 문제 해결 능력**이 매우 뛰어납니다.

- 답만 툭 던지는 게 아니라 **"사고 궤적(Thinking Trajectory)"** — 문제를 해결하는 단계별 논리 과정을 스스로 학습하도록 설계
- 의학, 법률, 화학, 금융 등 **고도의 전문 지식이 필요한 산업군(도메인)**에 특화된 비즈니스 솔루션으로 활발히 도입

### 2.4 오픈 웨이트(Open-Weight)를 통한 생태계 기여

LG AI연구원은 EXAONE의 주요 모델(EXAONE 3.0, 3.5, 4.5 등)을 외부 개발자와 연구자들이 가져다 쓸 수 있도록 **연구 목적으로 무상 공개(Open-Weight)**하고 있습니다.

---

## 3. 모델 라인업

| 모델명 | 파라미터 | 특징 |
|--------|----------|------|
| `exaone3.5:2.4b` | 2.4B | 경량, 빠른 응답, 로컬 실행 최적 |
| `exaone3.5:7.8b` | 7.8B | 한국어 전문 추론, 균형 잡힌 성능 |
| `exaone3.5:32b` | 32B | 고성능, 복잡한 전문 도메인 작업 |
| EXAONE 4.5 | 미공개 | 비전+언어 통합, 최신 멀티모달 |

---

## 4. 이 프로젝트에서 EXAONE 사용하기

### 4.1 Ollama로 로컬 실행 (권장 — 코드 수정 불필요)

```bash
# 1단계: EXAONE 모델 다운로드 (최초 1회)
ollama pull exaone3.5:2.4b   # ~1.5GB, 경량
ollama pull exaone3.5:7.8b   # ~5GB, 더 강력
```

```env
# .env 설정
LLM_PROVIDER=ollama
OLLAMA_MODEL=exaone3.5:2.4b
```

```bash
# 2단계: 헬스체크로 동작 확인
docker compose run --rm lab python catalog/health/00_healthcheck.py
```

### 4.2 환경별 모델 선택 가이드

| 환경 | 권장 모델 | 비고 |
|------|----------|------|
| GPU 없는 로컬 (RAM 8GB+) | `exaone3.5:2.4b` | 빠른 응답, 한국어 충분 |
| GPU 있는 개발 서버 | `exaone3.5:7.8b` | 추론 품질 향상 |
| 고성능 추론 필요 | `exaone3.5:32b` | VRAM 24GB+ 권장 |

### 4.3 기존 모델로 되돌리기

```env
# .env 에서 OLLAMA_MODEL만 변경
OLLAMA_MODEL=llama3.1:8b
```

---

## 5. EXAONE vs 주요 해외 모델 비교

| 항목 | EXAONE 3.5 | GPT-4o | Claude 3.5 |
|------|-----------|--------|-----------|
| 한국어 특화 | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i> | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-regular fa-star"></i><i class="fa-regular fa-star"></i> | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-regular fa-star"></i><i class="fa-regular fa-star"></i> |
| 한국 문화 이해 | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i> | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-regular fa-star"></i><i class="fa-regular fa-star"></i> | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-regular fa-star"></i><i class="fa-regular fa-star"></i> |
| 멀티모달 (4.5) | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i> | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i> | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-regular fa-star"></i> |
| 로컬 실행 가능 | <i class="fa-solid fa-circle-check"></i> (Ollama) | <i class="fa-solid fa-circle-xmark"></i> | <i class="fa-solid fa-circle-xmark"></i> |
| 오픈 웨이트 | <i class="fa-solid fa-circle-check"></i> | <i class="fa-solid fa-circle-xmark"></i> | <i class="fa-solid fa-circle-xmark"></i> |
| 한국어 토크나이저 효율 | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i> | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-regular fa-star"></i><i class="fa-regular fa-star"></i> | <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-regular fa-star"></i><i class="fa-regular fa-star"></i> |

> <i class="fa-solid fa-triangle-exclamation"></i>️ 비교 수치는 공개된 벤치마크 및 실사용 사례를 바탕으로 한 참고용 수치입니다.

---

## 6. 공식 링크

- HuggingFace: [LGAI-EXAONE](https://huggingface.co/LGAI-EXAONE)
- Ollama Hub: [ollama.com/library/exaone3.5](https://ollama.com/library/exaone3.5)
- LG AI연구원: [lgresearch.ai](https://lgresearch.ai)
