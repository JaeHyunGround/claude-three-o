# Claude Three-O - SEO + GEO + AAO 통합 최적화 플러그인

검색엔진, AI 엔진, AI 에이전트를 아우르는 통합 가시성 최적화 플러그인. 세 가지 축(SEO, GEO, AAO)을 병렬 분석하여 단일 점수(0-100)와 우선순위별 액션 플랜을 제공합니다.

[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blue)](https://claude.ai/claude-code)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-green)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Three-O** = **SEO** (검색엔진 최적화) + **GEO** (생성형 엔진 최적화) + **AAO** (에이전트 최적화)
>
> [SKYVENTURES](https://www.skyventures.co.kr/) 제작 | 한국 시장 특화

[English README](README.md)

## 목차

- [설치](#설치)
- [빠른 시작](#빠른-시작)
- [명령어](#명령어)
- [스코어링 시스템](#스코어링-시스템)
- [아키텍처](#아키텍처)
- [출력 포맷](#출력-포맷)
- [요구사항](#요구사항)

## 설치

### 플러그인 설치 (Claude Code 1.0.33+)

```bash
/plugin install claude-three-o
```

### 수동 설치

```bash
git clone https://github.com/skyventures/claude-three-o.git
cd claude-three-o && bash install.sh
```

## 빠른 시작

```bash
# 전체 3-pillar 분석
/three-o audit https://example.com

# 개별 모듈
/three-o seo audit https://example.com
/three-o geo audit "브랜드명"
/three-o aao audit https://example.com

# PDF 리포트 생성
/three-o report full --format pdf
```

## 명령어

### 메인 명령어

| 명령어 | 설명 |
|--------|------|
| `/three-o audit <url>` | 전체 3-pillar 분석 (SEO + GEO + AAO 병렬 실행) |
| `/three-o report [type]` | 통합 리포트 생성 (md / json / pdf) |
| `/three-o plan <business>` | 전략적 최적화 플랜 (타임라인 포함) |
| `/three-o competitor <u1> <u2>` | 크로스 pillar 경쟁사 벤치마킹 |
| `/three-o dashboard` | 대시보드 데이터 추출 |
| `/three-o setup` | API 키 설정 마법사 |

### SEO 모듈

| 명령어 | 설명 |
|--------|------|
| `/three-o seo audit <url>` | 전체 SEO 분석 |
| `/three-o seo technical <url>` | 기술적 SEO (메타, 보안, 모바일, 속도) |
| `/three-o seo naver <url>` | 네이버 특화 SEO (스마트스토어, 플레이스) |
| `/three-o seo content <url>` | 콘텐츠 품질 및 E-E-A-T 신호 |
| `/three-o seo schema <url>` | Schema.org 구조화 데이터 점검 |
| `/three-o seo images <url>` | 이미지 최적화 분석 |
| `/three-o seo drift baseline <url>` | SEO 베이스라인 캡처 |
| `/three-o seo drift compare <url>` | 베이스라인 대비 변화 감지 |

### GEO 모듈

| 명령어 | 설명 |
|--------|------|
| `/three-o geo audit <brand>` | 전체 GEO 분석 (5개 차원) |
| `/three-o geo mentions <brand>` | AI 플랫폼 브랜드 언급 추적 |
| `/three-o geo context <brand>` | 언급 맥락 품질 + 감성 분석 |
| `/three-o geo citability <url>` | 패시지 단위 AI 인용 가능성 |
| `/three-o geo entity <brand>` | 지식 그래프 엔티티 존재 여부 |
| `/three-o geo visibility <brand>` | AI 응답 내 포지션 랭킹 |
| `/three-o geo technical <url>` | AI 크롤러 접근성 점검 |
| `/three-o geo llms-txt <url>` | llms.txt 검증 및 생성 |
| `/three-o geo platforms <brand>` | 플랫폼별 분석 (ChatGPT, Perplexity, Gemini, Claude) |
| `/three-o geo drift <brand>` | GEO 변화 추이 감지 |

### AAO 모듈

| 명령어 | 설명 |
|--------|------|
| `/three-o aao audit <url>` | 전체 AAO 분석 |
| `/three-o aao selectability <url>` | 에이전트 선택성 신호 (6개 차원) |
| `/three-o aao conversion <url>` | 전환 퍼널 분석 |
| `/three-o aao data <url>` | 구조화 데이터 + 액션 스키마 감지 |
| `/three-o aao rendering <url>` | SSR, JS 의존도, 시맨틱 HTML |
| `/three-o aao entity <url>` | NAP 일관성 + sameAs 연결 |
| `/three-o aao feed <url>` | 상품 피드 검증 (Google Merchant / 네이버 EP) |
| `/three-o aao scenario <url>` | 업종별 에이전트 시나리오 테스트 |

## 스코어링 시스템

### Three-O 스코어 (0-100)

```
Three-O Score = SEO (35%) + GEO (35%) + AAO (30%)
```

| 등급 | 점수 | 의미 |
|------|------|------|
| A+ | 90-100 | 전 영역 우수 |
| A | 80-89 | 우수, 일부 소폭 개선 필요 |
| B+ | 70-79 | 양호, 개선 여지 있음 |
| B | 60-69 | 보통, 주요 갭 존재 |
| C+ | 50-59 | 미흡, 조치 필요 |
| C | 40-49 | 부족, 주요 문제 다수 |
| D | 20-39 | 매우 부족 |
| F | 0-19 | 거의 미존재 |

### SEO 스코어
기술적 SEO + 콘텐츠 품질 + 온페이지 + 스키마 + 퍼포먼스 + AI 준비도 + 이미지

### GEO 스코어 (기하 평균)
```
GEO = geometric_mean(MF^0.30 x CQ^0.25 x VR^0.20 x EP^0.15 x TA^0.10)
```
- **MF** (30%): 멘션 빈도 — AI 플랫폼에서 브랜드 언급 횟수
- **CQ** (25%): 맥락 품질 — 언급 컨텍스트의 정확성과 긍정도
- **VR** (20%): 가시성 랭킹 — AI 응답 내 포지션 순위
- **EP** (15%): 엔티티 존재 — 지식 그래프, 위키데이터 등록 여부
- **TA** (10%): 기술적 접근성 — AI 크롤러 접근 가능 여부

### AAO 스코어
선택성 + 전환 준비도 + 구조화 데이터 + 렌더링 + 엔티티 일관성

### 업종별 가중치 조정 (한국 시장)

| 업종 | 가중치 조정 |
|------|------------|
| 이커머스 (스마트스토어) | AAO +10% |
| 프랜차이즈 본사 | GEO +5%, AAO +5% |
| 학원/교육 | GEO +10% |
| 병원/의원 | GEO +10% |
| 음식점 | SEO +5% (네이버 플레이스) |

## 아키텍처

```
claude-three-o/
  .claude-plugin/
    plugin.json              # 플러그인 매니페스트
    marketplace.json         # 마켓플레이스 카탈로그
  skills/                    # 32개 스킬
    three-o/                 # 메인 오케스트레이터
    seo-*/                   # SEO 모듈 (10개)
    geo-*/                   # GEO 모듈 (9개)
    aao-*/                   # AAO 모듈 (8개)
    three-o-*/               # 크로스 커팅 (4개)
  agents/                    # 24개 서브에이전트
  hooks/                     # 품질 게이트 훅 (3개)
  scripts/                   # 42개 Python 스크립트
  schema/                    # Schema.org JSON-LD 템플릿
  tests/                     # 테스트 스위트 (41개)
  reports/                   # 생성된 리포트 (gitignore)
```

### 품질 게이트 훅

| 훅 | 역할 |
|----|------|
| `validate_quality.py` | INP 강제(FID 금지), HowTo 금지, FAQ 정부/의료만, 하드코딩 경로 방지 |
| `check_cwv.py` | Core Web Vitals 용어 검증 |
| `check_schema.py` | 스키마 추천 규칙 강제 |

## 출력 포맷

| 포맷 | 명령어 | 용도 |
|------|--------|------|
| 터미널 | (기본값) | 빠른 분석, 컬러 바 시각화 |
| JSON | `--json` | API 연동, 데이터 파이프라인 |
| Markdown | `--format md` | 문서화, PR 설명 |
| PDF | `--format pdf` | 클라이언트 납품, 프레젠테이션 |

### PDF 리포트 특징
- 한글 텍스트 완벽 지원 (AppleGothic / NanumGothic)
- 컬러 코딩 점수 시각화 (녹/황/적)
- 6페이지 구성: 타이틀, Executive Summary, SEO, GEO, AAO, 액션 플랜
- 우선순위 액션 테이블 (P0/P1/P2)
- SKYVENTURES 브랜딩

## 요구사항

- Python 3.9+
- Claude Code CLI
- `httpx` (HTTP 클라이언트)
- `fpdf2` (PDF 생성)
- 선택사항: AI 플랫폼 라이브 데이터용 API 키

## 라이선스

MIT License

---

[SKYVENTURES](https://www.skyventures.co.kr/) 제작 | Powered by Claude Code
