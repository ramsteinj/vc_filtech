# vc_filtech — FilTech Bid Assistant

발전소(가스터빈 흡기·공조) 입찰 공고 중 (주)필텍 공기필터 제품에 적합한 공고를 찾고, 공고의 핵심 요구사항을 회사 제품 사양·시험성적서·인증·납품실적과 비교해 **충족 / 보완 필요 / 확인 필요**로 판정한 뒤 **Compliance Matrix, 입찰 체크리스트, 발주처 기술질의서, 검토 보고서(PDF)** 초안을 만드는 Web App.

> 현재 상태: **요구사항 정의 완료, 구현 전 (M0 착수 예정)** — 진행 현황은 [specs/13-roadmap.md](specs/13-roadmap.md)

## 주요 기능

**입찰담당자**
- ID/비밀번호 로그인
- 대시보드: 총 입찰 건수 · 확인 건수 · 미확인 건수 + 공고 목록(적합도, 마감일, 판정 요약)
- 공고 상세: ① 핵심 요구사항 → ② 회사 자료 비교 → ③ 판정·근거·자동 답변(수정 가능) → ④ 초안 생성 → ⑤ 확인·수정·PDF 다운로드

**관리자**
- 상단 우측 로그인, 기본 계정 자동 생성 (`admin` / `admin1234!` — 최초 로그인 후 변경 권장)
- 입찰담당자 추가·관리
- 회사 정보 · 제품 · 시험성적서 · 인증서 · 납품실적 CRUD (TXT / DOCX / HWP / HWPX / PDF 업로드 또는 텍스트 입력, 분류별 메타데이터 자동 추출·수정)
- 입찰 공고 + 다중 첨부 등록·수정·삭제, 핵심 요구사항 자동 추출
- LLM 선택(ChatGPT / Claude / Gemini), API Key·모델(기본 Claude Opus 5.5)·프롬프트·튜닝 설정 — 모두 PostgreSQL 저장
- API Key 미설정 시: 관리자 로그인 페이지로 이동 → 로그인 후 바로 API Key 입력 화면

## 기술 스택

| 영역 | 스택 |
|---|---|
| Frontend | Vue.js 3, Vite, Bootstrap 5.0, HTML5/CSS3 (SPA) |
| Backend | Python 3.12, Django 5.2, Django REST Framework, Django ORM |
| Database | PostgreSQL 16 |
| LLM | OpenAI / Anthropic / Google Gemini SDK |

```
Vue.js SPA ──HTTP/JSON──▶ Django REST Framework ──Django ORM──▶ PostgreSQL
```

## 저장소 구조

```
CLAUDE.md        Claude Code 작업 지침 (vibe coding 규칙)
specs/           상세 요구사항 (00 개요 ~ 13 로드맵)
initial-data/    초기 데이터 (읽기 전용)
  company/         회사 자료: 인증서 3, 기술사양서 6, 납품실적 1, 시험성적서 9 (PoC용 가상 자료, PDF)
  bid_sample/      입찰 공고 샘플: won/ 8건 (HWP·HWPX·XLS·XLSX·PDF), lost/ (비어 있음)
backend/         Django (예정)
frontend/        Vue 3 (예정)
```

## 스펙 문서

| # | 문서 |
|---|---|
| 00 | [개요 · 용어 · 결정 사항](specs/00-overview.md) |
| 01 | [아키텍처 · 디렉터리 · 환경 변수](specs/01-architecture.md) |
| 02 | [데이터 모델](specs/02-data-model.md) |
| 03 | [인증 · 권한 · API Key 게이트](specs/03-auth-and-access.md) |
| 04 | [관리자 기능](specs/04-admin-features.md) |
| 05 | [입찰담당자 기능](specs/05-bid-manager-features.md) |
| 06 | [문서 처리 (HWP 파싱 · 분류 · 메타데이터)](specs/06-document-processing.md) |
| 07 | [LLM 연동 · 프롬프트 · 튜닝](specs/07-llm-integration.md) |
| 08 | [요구사항 추출 · 판정 규칙](specs/08-compliance-evaluation.md) |
| 09 | [초안 · PDF 보고서](specs/09-drafts-and-reports.md) |
| 10 | [REST API](specs/10-api.md) |
| 11 | [Frontend](specs/11-frontend.md) |
| 12 | [초기 데이터 · 테스트 시나리오](specs/12-initial-data.md) |
| 13 | [로드맵](specs/13-roadmap.md) |

## 빠른 시작 (구현 후 사용 예정)

```bash
cp .env.example .env              # DJANGO_SECRET_KEY, FIELD_ENCRYPTION_KEY 설정
docker compose up -d db

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate          # 기본 관리자 admin / admin1234! 자동 생성
python manage.py load_initial_data
python manage.py runserver 8000
python manage.py run_jobs         # 별도 터미널: 백그라운드 작업 워커

cd ../frontend
npm install && npm run dev        # http://localhost:5173
```

첫 접속 시 LLM API Key가 없으므로 관리자 로그인 → API Key 입력 화면으로 안내됩니다.

## 주의

- `initial-data/company/`의 자료는 PoC 테스트용 **가상 자료**입니다.
- 생성되는 모든 판정·문서는 **초안**이며 제출 전 담당자 검토가 필요합니다.
