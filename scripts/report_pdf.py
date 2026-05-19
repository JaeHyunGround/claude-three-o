"""PDF report generator for Three-O platform. Supports Korean text."""

import argparse
import json
import os
from datetime import datetime
from typing import Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from config import VERSION


KOREAN_FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/nanum-gothic/NanumGothic.ttf",
]

COLORS = {
    "primary": (41, 98, 255),
    "secondary": (100, 116, 139),
    "success": (34, 197, 94),
    "warning": (245, 158, 11),
    "danger": (239, 68, 68),
    "text": (30, 41, 59),
    "light_bg": (248, 250, 252),
    "border": (226, 232, 240),
    "info_bg": (239, 246, 255),
    "info_border": (147, 197, 253),
}

SEVERITY_COLORS = {
    "critical": COLORS["danger"],
    "high": (220, 38, 38),
    "medium": COLORS["warning"],
    "warning": COLORS["warning"],
    "low": COLORS["secondary"],
    "info": (59, 130, 246),
}

DIMENSION_LABELS_BIZ = {
    "meta_quality": "검색결과 노출 품질",
    "security": "보안 상태",
    "mobile": "모바일 호환성",
    "headings": "콘텐츠 구조",
    "images": "이미지 최적화",
    "performance": "페이지 속도",
    "structured_data": "구조화 데이터",
    "crawlability": "검색엔진 접근성",
    "heading_structure": "제목 구조(H1~H6)",
    "image_optimization": "이미지 최적화",
    "link_health": "링크 건전성",
    "mobile_readiness": "모바일 호환성",
    "indexability": "색인 가능성",
    "security_signals": "보안 신호",
    "performance_signals": "성능 신호",
    "experience": "실제 경험 근거",
    "expertise": "전문성",
    "authoritativeness": "권위성",
    "trust": "신뢰성",
    "passage_clarity": "문장 명확성",
    "factual_density": "사실 정보 밀도",
    "citation_pattern": "인용 패턴",
    "self_containment": "독립 이해 가능성",
    "quote_readiness": "인용 준비도",
    "structural_format": "구조적 형식",
    "authority_signals": "권위 신호",
    "polarity_strength": "브랜드 인식 강도",
    "consistency": "언급 일관성",
    "coverage": "AI 노출 범위",
    "platform_alignment": "플랫폼간 정합성",
    "signal_diversity": "신호 다양성",
    "mention_frequency": "AI 언급 빈도",
    "context_quality": "맥락 품질",
    "visibility_ranking": "가시성 순위",
    "entity_presence": "엔티티 존재감",
    "technical_accessibility": "기술적 접근성",
    "reviews_ratings": "리뷰 및 평점",
    "info_completeness": "정보 완성도",
    "api_booking": "예약/주문 연동",
    "trust_signals": "신뢰 지표",
    "freshness": "정보 최신성",
    "cta_quality": "행동유도 버튼(CTA)",
    "form_accessibility": "양식 접근성",
    "flow_clarity": "전환 흐름",
    "mobile_conversion": "모바일 전환",
    "deep_linking": "딥링크 지원",
    "confirmation": "확인 체계",
    "attribute_completeness": "속성 완성도",
    "image_quality": "이미지 품질",
    "pricing_accuracy": "가격 정확성",
    "category_mapping": "카테고리 매핑",
    "data_quality": "데이터 품질",
    "feed_freshness": "피드 최신성",
}

PILLAR_LABELS_BIZ = {
    "seo": "검색 노출 현황",
    "geo": "AI 검색 노출 현황",
    "aao": "AI 에이전트 대응 현황",
}

PILLAR_DESCRIPTIONS_BIZ = {
    "seo": "구글, 네이버 등 검색엔진에서 고객이 귀사를 쉽게 찾을 수 있는지를 나타냅니다. 점수가 높을수록 검색 결과 상위에 노출될 가능성이 큽니다.",
    "geo": "ChatGPT, Perplexity, Gemini 등 AI 서비스가 귀사 브랜드를 어떻게 언급하고 추천하는지를 나타냅니다. AI 검색 시대에 브랜드 가시성의 핵심 지표입니다.",
    "aao": "AI 비서(에이전트)가 귀사를 고객에게 추천하고, 예약이나 구매까지 연결할 수 있는 준비 상태를 나타냅니다. 향후 AI 커머스 전환의 핵심입니다.",
}

ISSUE_IMPACT_MAP = {
    "meta description": "검색 결과에 사이트 설명이 표시되지 않아 클릭률이 낮아질 수 있습니다",
    "canonical": "중복 페이지로 인해 검색 순위가 분산될 수 있습니다",
    "hsts": "보안 인증이 부족하여 방문자 신뢰가 떨어질 수 있습니다",
    "viewport": "모바일에서 페이지가 제대로 표시되지 않을 수 있습니다",
    "h1": "페이지 주제가 불명확하여 검색 순위에 영향을 줄 수 있습니다",
    "alt": "이미지 검색에서 노출 기회를 놓치고 있습니다",
    "title length": "검색 결과에서 제목이 잘리거나 불완전하게 표시됩니다",
    "schema": "AI와 검색엔진이 사업 정보를 자동으로 이해하기 어렵습니다",
    "structured data": "AI 비서가 귀사 정보를 정확히 파악하기 어렵습니다",
    "robots": "검색엔진이 사이트를 제대로 탐색할 수 없습니다",
    "ssl": "보안 연결 미설정으로 검색 순위 불이익을 받습니다",
    "sitemap": "검색엔진이 모든 페이지를 발견하지 못할 수 있습니다",
    "noindex": "이 페이지가 검색 결과에 표시되지 않도록 설정되어 있습니다",
    "open graph": "SNS 공유 시 미리보기가 표시되지 않아 공유 효과가 떨어집니다",
    "speed": "페이지 로딩이 느려 방문자 이탈률이 높아질 수 있습니다",
    "mobile": "모바일 사용자 경험이 좋지 않아 이탈이 발생할 수 있습니다",
    "review": "리뷰/평점이 부족하여 AI 추천 우선순위가 낮아질 수 있습니다",
    "booking": "온라인 예약/주문이 불가하여 AI 에이전트가 전환을 완료할 수 없습니다",
    "freshness": "정보가 오래되어 검색엔진과 AI가 신뢰도를 낮게 평가할 수 있습니다",
    "crawl": "검색엔진 봇이 사이트에 접근하기 어려운 상태입니다",
    "entity": "브랜드 정보가 일관되지 않아 AI가 혼동할 수 있습니다",
    "citation": "AI가 인용하기 어려운 콘텐츠 구조입니다",
    "mention": "AI 서비스에서 브랜드 언급 빈도가 낮습니다",
    "sentiment": "AI 서비스에서 브랜드에 대한 부정적 언급이 감지되었습니다",
    "factual density": "사실 정보(수치, 날짜, 통계)가 부족하여 AI가 인용하기 어렵습니다",
    "login required": "로그인 필수로 AI 에이전트가 전환을 완료할 수 없습니다",
    "cta quality": "행동유도 버튼(CTA)이 불명확하여 전환율이 낮을 수 있습니다",
    "performance signal": "페이지 로딩 성능이 부족하여 사용자 이탈이 발생할 수 있습니다",
    "flow completeness": "전환 흐름이 불완전하여 사용자가 이탈할 수 있습니다",
    "guest": "비회원 이용이 불가하여 신규 고객 전환에 장벽이 됩니다",
    "preload": "페이지 로딩 성능이 부족하여 사용자 이탈이 발생할 수 있습니다",
    "async": "페이지 로딩 성능이 부족하여 사용자 이탈이 발생할 수 있습니다",
}

REC_TRANSLATIONS_BIZ = {
    "Add meta description (120-160 chars)": {
        "title": "메타 설명 추가 (120~160자)",
        "detail": "페이지 내용을 요약하는 매력적인 설명을 작성하세요. 검색 결과에서 클릭률을 크게 높일 수 있습니다.",
    },
    "Optimize title tag length to 30-60 characters": {
        "title": "페이지 제목 최적화 (30~60자)",
        "detail": "검색 결과에 표시되는 제목을 적정 길이로 조정하세요. 핵심 키워드를 앞부분에 배치하면 효과적입니다.",
    },
    "Add canonical URL tag": {
        "title": "대표 URL 태그 추가",
        "detail": "중복 페이지 문제를 방지하기 위해 대표 URL을 지정하세요.",
    },
    "Fix heading hierarchy (single H1, proper H2-H3 nesting)": {
        "title": "제목 구조 정리 (H1 하나, H2~H3 순서 맞추기)",
        "detail": "페이지 주제를 명확히 하는 대제목(H1)을 하나만 두고, 소제목을 계층적으로 구성하세요.",
    },
    "Enable HSTS header": {
        "title": "보안 헤더(HSTS) 활성화",
        "detail": "HTTPS 연결을 강제하는 보안 설정을 추가하여 방문자 신뢰를 높이세요.",
    },
    "Add viewport meta tag for mobile": {
        "title": "모바일 화면 최적화 태그 추가",
        "detail": "모바일 기기에서 페이지가 올바르게 표시되도록 설정하세요. 모바일 검색 순위에 직접 영향을 줍니다.",
    },
    "Add alt text to all images": {
        "title": "모든 이미지에 설명 텍스트 추가",
        "detail": "이미지에 설명을 추가하면 이미지 검색 노출이 증가하고, 접근성이 향상됩니다.",
    },
    "Add definition-style sentences for AI citation": {
        "title": "AI 인용을 위한 정의형 문장 추가",
        "detail": "\"[브랜드]는 ~입니다\" 형태의 명확한 문장을 작성하세요. AI가 가장 많이 인용하는 형식입니다.",
    },
    "Increase factual density with specific numbers and data": {
        "title": "구체적 수치/데이터로 콘텐츠 보강",
        "detail": "통계, 날짜, 구체적 숫자를 추가하세요. Perplexity와 Claude는 데이터 기반 콘텐츠를 선호합니다.",
    },
    "Add source attributions and references": {
        "title": "출처 및 참고문헌 표시",
        "detail": "공신력 있는 연구, 보고서, 공식 출처를 인용하세요. AI의 신뢰도 평가에 큰 영향을 줍니다.",
    },
    "Improve content structure with headings and lists": {
        "title": "제목과 목록으로 콘텐츠 구조화",
        "detail": "소제목(H2/H3), 글머리 기호, 표 등으로 정보를 체계적으로 정리하세요. AI가 구조화된 콘텐츠를 더 잘 이해합니다.",
    },
    "Strengthen E-E-A-T signals for Gemini": {
        "title": "전문성·권위·신뢰 신호 강화",
        "detail": "저자 정보, 발행일, 전문가 인용, 인증 정보를 추가하세요. Google AI와 Gemini가 중요하게 평가합니다.",
    },
    "Create and publish llms.txt file": {
        "title": "AI용 브랜드 정보 파일(llms.txt) 게시",
        "detail": "AI가 귀사 정보를 정확히 파악하도록 핵심 정보를 정리한 텍스트 파일을 웹사이트에 게시하세요.",
    },
    "Add JSON-LD structured data with business entity": {
        "title": "비즈니스 구조화 데이터(JSON-LD) 추가",
        "detail": "업종에 맞는 스키마 마크업을 추가하면 AI 에이전트가 귀사 정보를 정확히 파악할 수 있습니다.",
    },
    "Add Schema.org potentialAction for agent execution": {
        "title": "AI 에이전트용 액션 스키마 추가",
        "detail": "예약, 주문, 검색 등의 액션을 스키마로 정의하면 AI 에이전트가 자동으로 작업을 수행할 수 있습니다.",
    },
    "Implement review collection and schema markup": {
        "title": "리뷰 수집 및 평점 마크업 구현",
        "detail": "고객 리뷰를 체계적으로 수집하고 평점 데이터를 구조화하세요. AI 추천 시 리뷰가 핵심 선택 기준입니다.",
    },
    "Complete all business information fields": {
        "title": "비즈니스 기본 정보 완성",
        "detail": "이름, 설명, 주소, 전화번호, 운영시간, 가격 등 필수 정보를 빠짐없이 기재하세요.",
    },
    "Add trust signals (certifications, business registration, le": {
        "title": "신뢰 지표 추가 (인증, 사업자등록, 법적 정보)",
        "detail": "사업자등록번호, 인증 마크, 개인정보처리방침 등을 표시하여 신뢰도를 높이세요.",
    },
    "Improve freshness indicators (dates, last-modified, dynamic cont": {
        "title": "최신성 지표 개선 (날짜, 업데이트 정보)",
        "detail": "최근 날짜, 수정일, 실시간 정보를 표시하세요. AI는 최신 정보를 가진 사이트를 더 높이 평가합니다.",
    },
}

SEVERITY_LABELS_BIZ = {
    "critical": "즉시 조치 필요",
    "high": "1주 이내 조치",
    "medium": "1개월 이내 개선",
    "warning": "개선 권장",
    "low": "참고 사항",
}


def _score_to_grade(score: float) -> tuple:
    if score >= 90:
        return "A+", "매우 우수"
    if score >= 80:
        return "A", "우수"
    if score >= 70:
        return "B+", "양호"
    if score >= 60:
        return "B", "보통"
    if score >= 50:
        return "C", "개선 필요"
    if score >= 40:
        return "D", "미흡"
    return "F", "심각한 개선 필요"


def _translate_issue(message: str) -> str:
    msg_lower = message.lower()
    for pattern, translation in ISSUE_IMPACT_MAP.items():
        if pattern in msg_lower:
            return translation
    return message


EFFORT_LABELS_BIZ = {
    "< 1 hour": "1시간 미만",
    "1-4 hours": "1~4시간",
    "1-2 days": "1~2일",
    "1+ week": "1주 이상",
}
IMPACT_LABELS_BIZ = {
    "+2-5 pts": "+2~5점",
    "+5-10 pts": "+5~10점",
    "+10-20 pts": "+10~20점",
    "+15-30 pts": "+15~30점",
}


def _translate_rec(rec: dict) -> dict:
    translated = dict(rec)
    title = rec.get("title", "")
    for eng_title, kr in REC_TRANSLATIONS_BIZ.items():
        if title.startswith(eng_title[:40]):
            translated["title"] = kr["title"]
            translated["detail"] = kr["detail"]
            break
    effort = translated.get("effort_estimate", "")
    if effort in EFFORT_LABELS_BIZ:
        translated["effort_estimate"] = EFFORT_LABELS_BIZ[effort]
    impact = translated.get("impact_estimate", "")
    if impact in IMPACT_LABELS_BIZ:
        translated["impact_estimate"] = IMPACT_LABELS_BIZ[impact]
    return translated


def _dim_label(key: str) -> str:
    return DIMENSION_LABELS_BIZ.get(key, key.replace("_", " ").title())


class ThreeOPDF(FPDF):
    """Custom PDF class for Three-O reports."""

    def __init__(self, brand: str = ""):
        super().__init__()
        self.brand = brand
        self._setup_fonts()

    def _setup_fonts(self):
        """Register Korean font if available."""
        self.korean_available = False
        for font_path in KOREAN_FONT_PATHS:
            if os.path.exists(font_path):
                try:
                    self.add_font("Korean", "", font_path)
                    self.add_font("Korean", "B", font_path)
                    self.korean_available = True
                    break
                except Exception:
                    continue

    def _set_font(self, style="", size=10):
        """Set font with Korean fallback."""
        if self.korean_available:
            self.set_font("Korean", style, size)
        else:
            self.set_font("Helvetica", style, size)

    def header(self):
        self._set_font("B", 9)
        self.set_text_color(*COLORS["secondary"])
        self.cell(0, 8, f"Three-O Report | {self.brand}", 0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(0, 8, datetime.now().strftime("%Y-%m-%d"), 0, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*COLORS["border"])
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self._set_font("", 8)
        self.set_text_color(*COLORS["secondary"])
        self.cell(0, 10, f"Generated by Three-O v{VERSION} | Page {self.page_no()}/{{nb}}", 0, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)

    # ─── Shared helpers ───

    def _section_title(self, title: str):
        self._set_font("B", 16)
        self.set_text_color(*COLORS["primary"])
        self.cell(0, 12, title, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*COLORS["primary"])
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(8)

    def _draw_score_bar(self, label: str, score: float, label_width: int = 50):
        self._set_font("", 9)
        self.set_text_color(*COLORS["text"])
        self.cell(label_width, 7, label, 0, new_x=XPos.RIGHT, new_y=YPos.TOP)

        bar_x = self.get_x()
        bar_y = self.get_y() + 1.5
        bar_width = 80
        bar_height = 4

        self.set_fill_color(*COLORS["border"])
        self.rect(bar_x, bar_y, bar_width, bar_height, "F")

        if score >= 70:
            fill_color = COLORS["success"]
        elif score >= 50:
            fill_color = COLORS["warning"]
        else:
            fill_color = COLORS["danger"]

        fill_width = bar_width * (score / 100)
        self.set_fill_color(*fill_color)
        self.rect(bar_x, bar_y, fill_width, bar_height, "F")

        self.set_x(bar_x + bar_width + 3)
        self._set_font("B", 9)
        self.cell(20, 7, f"{score:.0f}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _draw_score_circle(self, score: float, grade: str):
        self._set_font("B", 48)
        if score >= 70:
            self.set_text_color(*COLORS["success"])
        elif score >= 50:
            self.set_text_color(*COLORS["warning"])
        else:
            self.set_text_color(*COLORS["danger"])
        self.cell(0, 25, f"{score:.1f}", 0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._set_font("B", 18)
        self.cell(0, 10, f"/ 100  ({grade})", 0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _info_box(self, text: str):
        self.set_fill_color(*COLORS["info_bg"])
        self.set_draw_color(*COLORS["info_border"])
        x = self.get_x()
        y = self.get_y()
        self._set_font("", 8)
        self.set_text_color(*COLORS["text"])
        self.rect(x, y, 190, 14, "DF")
        self.set_xy(x + 3, y + 2)
        self.multi_cell(184, 5, text, 0, "L")
        self.set_y(y + 16)

    # ═══════════════════════════════════════════════
    #  TITLE PAGE (shared)
    # ═══════════════════════════════════════════════

    def add_title_page(self, data: dict):
        self.add_page()
        self.ln(40)

        self._set_font("B", 28)
        self.set_text_color(*COLORS["primary"])
        self.cell(0, 15, "Three-O", 0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self._set_font("", 14)
        self.set_text_color(*COLORS["secondary"])
        self.cell(0, 10, "SEO + GEO + AAO Unified Optimization Report", 0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.ln(20)
        self._set_font("B", 22)
        self.set_text_color(*COLORS["text"])
        self.cell(0, 12, self.brand, 0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.ln(15)
        score = data.get("three_o_score", {})
        score_val = score.get("score", 0)
        grade = score.get("grade", "N/A")
        self._draw_score_circle(score_val, grade)

        self.ln(20)
        self._set_font("", 11)
        self.set_text_color(*COLORS["secondary"])
        self.cell(0, 8, f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 8, "Powered by JaeHyunGround Three-O Platform", 0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ═══════════════════════════════════════════════
    #  DEVELOPER MODE (original)
    # ═══════════════════════════════════════════════

    def add_executive_summary(self, data: dict):
        self.add_page()
        self._section_title("Executive Summary")

        score = data.get("three_o_score", {})
        pillars = score.get("pillars", {})

        if pillars:
            self._set_font("B", 11)
            self.set_text_color(*COLORS["text"])
            self.cell(0, 10, "Pillar Scores", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            for pillar_name, pillar_data in pillars.items():
                p_score = pillar_data.get("score", 0) if isinstance(pillar_data, dict) else pillar_data
                self._draw_score_bar(pillar_name.upper(), float(p_score))

        self.ln(10)
        top_issues = data.get("top_issues", [])
        if top_issues:
            self._set_font("B", 11)
            self.set_text_color(*COLORS["text"])
            self.cell(0, 10, "Top Priority Actions", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            for i, issue in enumerate(top_issues[:5], 1):
                severity = issue.get("severity", "medium")
                color = SEVERITY_COLORS.get(severity, COLORS["secondary"])
                self._set_font("B", 9)
                self.set_text_color(*color)
                self.cell(8, 7, f"{i}.", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_fill_color(*color)
                self.cell(18, 7, severity.upper(), 0, align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_text_color(*COLORS["text"])
                self._set_font("", 9)
                self.cell(0, 7, f"  {issue.get('message', '')}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def add_pillar_section(self, pillar: str, data: dict):
        pillar_data = data.get(pillar, {})
        if not pillar_data:
            return

        self.add_page()
        pillar_titles = {"seo": "SEO Analysis", "geo": "GEO Analysis", "aao": "AAO Analysis"}
        self._section_title(pillar_titles.get(pillar, pillar.upper()))

        p_score = pillar_data.get("score", 0)
        self._set_font("B", 14)
        self.set_text_color(*COLORS["text"])
        self.cell(0, 10, f"Score: {p_score}/100", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)

        dimensions = pillar_data.get("dimensions", {})
        if dimensions:
            self._set_font("B", 10)
            self.cell(0, 8, "Dimension Breakdown", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(3)
            for dim_name, dim_val in dimensions.items():
                score_val = dim_val if isinstance(dim_val, (int, float)) else dim_val.get("score", 0)
                label = dim_name.replace("_", " ").title()
                self._draw_score_bar(label, float(score_val))

        if pillar == "geo":
            platform_breakdown = pillar_data.get("platform_breakdown", {})
            if platform_breakdown:
                self.ln(5)
                self._set_font("B", 10)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 8, "Platform GEO Scores", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)
                for p_name, p_data in platform_breakdown.items():
                    p_score = p_data.get("geo_score", 0) if isinstance(p_data, dict) else p_data
                    self._draw_score_bar(p_name.capitalize(), float(p_score))

        if pillar == "aao":
            industry = pillar_data.get("industry_detected", "")
            if industry and industry != "general":
                self.ln(5)
                self._set_font("B", 10)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 8, f"Industry Detected: {industry.title()}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(2)
                weights = pillar_data.get("weights_applied", {})
                if weights:
                    self._set_font("", 8)
                    self.set_text_color(*COLORS["secondary"])
                    w_str = ", ".join(f"{k.replace('_', ' ')}: {v:.0%}" for k, v in weights.items())
                    self.cell(0, 6, f"Adjusted weights: {w_str}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            correlation = pillar_data.get("correlation", {})
            if correlation and correlation.get("applied"):
                self.ln(3)
                self._set_font("B", 9)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 7, "Signal Correlations:", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                for c in correlation["applied"][:5]:
                    prefix = "+" if c["value"] > 0 else ""
                    color = COLORS["success"] if c["value"] > 0 else COLORS["danger"]
                    self._set_font("", 8)
                    self.set_text_color(*color)
                    self.cell(5, 5, "", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                    self.cell(0, 5, f"{prefix}{c['value']:.0f} {c['reason']}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.ln(8)
        issues = pillar_data.get("issues", [])
        if issues:
            self._set_font("B", 10)
            self.set_text_color(*COLORS["text"])
            self.cell(0, 8, f"Issues ({len(issues)})", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(2)
            for issue in issues[:10]:
                severity = issue.get("severity", "info")
                color = SEVERITY_COLORS.get(severity, COLORS["secondary"])
                self._set_font("", 9)
                self.set_text_color(*color)
                self.cell(5, 6, "", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_fill_color(*color)
                self.cell(16, 6, severity.upper(), 0, align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 6, f"  {issue.get('message', '')}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def add_recommendations(self, data: dict):
        from recommendations import generate_recommendations
        rec_data = generate_recommendations(data)

        if not rec_data.get("recommendations"):
            return

        self.add_page()
        self._section_title("Recommendations")

        industry = rec_data.get("industry", "general")
        if industry != "general":
            self._set_font("", 10)
            self.set_text_color(*COLORS["secondary"])
            self.cell(0, 7, f"Industry: {industry.title()} | {rec_data['total']} recommendations generated", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(5)

        if rec_data.get("quick_wins"):
            self._set_font("B", 11)
            self.set_text_color(*COLORS["success"])
            self.cell(0, 8, "Quick Wins (High impact, Low effort)", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(2)
            for i, r in enumerate(rec_data["quick_wins"][:4], 1):
                self._set_font("B", 9)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 6, f"{i}. {r['title']}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self._set_font("", 8)
                self.set_text_color(*COLORS["secondary"])
                detail = r["detail"][:100] + ("..." if len(r["detail"]) > 100 else "")
                self.cell(5, 5, "", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.cell(0, 5, detail, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.cell(5, 5, "", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_text_color(59, 130, 246)
                self.cell(0, 5, f"Effort: {r['effort_estimate']} | Impact: {r['impact_estimate']}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(2)

        if rec_data.get("strategic"):
            self.ln(3)
            self._set_font("B", 11)
            self.set_text_color(*COLORS["primary"])
            self.cell(0, 8, "Strategic Investments", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(2)
            for i, r in enumerate(rec_data["strategic"][:3], 1):
                self._set_font("B", 9)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 6, f"{i}. {r['title']}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self._set_font("", 8)
                self.set_text_color(*COLORS["secondary"])
                detail = r["detail"][:100] + ("..." if len(r["detail"]) > 100 else "")
                self.cell(5, 5, "", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.cell(0, 5, detail, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(2)

    def add_action_plan(self, data: dict):
        self.add_page()
        self._section_title("Action Plan")

        all_issues = []
        for pillar in ["seo", "geo", "aao"]:
            for issue in data.get(pillar, {}).get("issues", []):
                all_issues.append({"pillar": pillar.upper(), **issue})

        severity_order = {"critical": 0, "high": 1, "medium": 2, "warning": 3, "low": 4}
        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 5))

        col_widths = [15, 18, 20, 120]
        headers = ["#", "Priority", "Area", "Action"]
        self._set_font("B", 9)
        self.set_fill_color(*COLORS["light_bg"])
        for i, (h, w) in enumerate(zip(headers, col_widths)):
            self.cell(w, 7, h, 1, align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.ln()

        self._set_font("", 8)
        for i, issue in enumerate(all_issues[:20], 1):
            severity = issue.get("severity", "low")
            priority = "P0" if severity == "critical" else "P1" if severity == "high" else "P2"
            self.set_text_color(*COLORS["text"])
            self.cell(col_widths[0], 6, str(i), 1, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
            color = SEVERITY_COLORS.get(severity, COLORS["secondary"])
            self.set_text_color(*color)
            self.cell(col_widths[1], 6, priority, 1, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_text_color(*COLORS["text"])
            self.cell(col_widths[2], 6, issue.get("pillar", ""), 1, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
            msg = issue.get("message", "")[:65]
            self.cell(col_widths[3], 6, msg, 1, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.ln()

    # ═══════════════════════════════════════════════
    #  BUSINESS MODE
    # ═══════════════════════════════════════════════

    def add_overview_business(self, data: dict):
        self.add_page()
        self._section_title("한눈에 보기")

        score = data.get("three_o_score", {})
        overall = score.get("score", 0)
        grade, grade_text = _score_to_grade(overall)

        self._set_font("B", 12)
        self.set_text_color(*COLORS["text"])
        self.cell(0, 8, f"종합 점수: {overall:.1f}/100 ({grade} - {grade_text})", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)

        self._info_box(
            "Three-O 점수는 검색 노출(SEO), AI 검색 노출(GEO), AI 에이전트 대응(AAO) "
            "세 가지 영역을 종합 평가한 점수입니다. 70점 이상이면 양호, 50점 미만이면 개선이 필요합니다."
        )
        self.ln(3)

        pillars = score.get("pillars", {})
        for pillar_key in ["seo", "geo", "aao"]:
            pillar_data = pillars.get(pillar_key, {})
            p_score = pillar_data.get("score", 0) if isinstance(pillar_data, dict) else pillar_data
            p_score = float(p_score)
            p_grade, p_grade_text = _score_to_grade(p_score)
            label = PILLAR_LABELS_BIZ.get(pillar_key, pillar_key.upper())

            self._draw_score_bar(f"{label} ({p_grade})", p_score, 65)

        self.ln(8)
        self._set_font("B", 11)
        self.set_text_color(*COLORS["text"])
        self.cell(0, 8, "각 영역이 의미하는 것", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

        for pillar_key in ["seo", "geo", "aao"]:
            label = PILLAR_LABELS_BIZ[pillar_key]
            desc = PILLAR_DESCRIPTIONS_BIZ[pillar_key]
            self._set_font("B", 9)
            self.set_text_color(*COLORS["primary"])
            self.cell(0, 6, label, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self._set_font("", 8)
            self.set_text_color(*COLORS["secondary"])
            self.multi_cell(0, 5, desc)
            self.ln(3)

        top_issues = data.get("top_issues", [])
        if top_issues:
            self.ln(3)
            self._set_font("B", 11)
            self.set_text_color(*COLORS["danger"])
            self.cell(0, 8, "가장 시급한 개선 사항", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(2)

            for i, issue in enumerate(top_issues[:5], 1):
                severity = issue.get("severity", "medium")
                sev_label = SEVERITY_LABELS_BIZ.get(severity, severity)
                color = SEVERITY_COLORS.get(severity, COLORS["secondary"])
                msg = _translate_issue(issue.get("message", ""))

                self._set_font("B", 9)
                self.set_text_color(*color)
                self.cell(8, 7, f"{i}.", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_fill_color(*color)
                self.set_text_color(255, 255, 255)
                self.cell(30, 7, sev_label, 0, align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_text_color(*COLORS["text"])
                self._set_font("", 9)
                self.cell(0, 7, f"  {msg[:80]}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def add_pillar_business(self, pillar: str, data: dict):
        pillar_data = data.get(pillar, {})
        if not pillar_data:
            return

        self.add_page()
        title = PILLAR_LABELS_BIZ.get(pillar, pillar.upper())
        self._section_title(title)

        p_score = pillar_data.get("score", 0)
        grade, grade_text = _score_to_grade(float(p_score))

        self._set_font("B", 14)
        if p_score >= 70:
            self.set_text_color(*COLORS["success"])
        elif p_score >= 50:
            self.set_text_color(*COLORS["warning"])
        else:
            self.set_text_color(*COLORS["danger"])
        self.cell(0, 10, f"{grade} ({grade_text}) - {p_score}/100", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

        self._info_box(PILLAR_DESCRIPTIONS_BIZ.get(pillar, ""))
        self.ln(3)

        dimensions = pillar_data.get("dimensions", {})
        if dimensions:
            self._set_font("B", 10)
            self.set_text_color(*COLORS["text"])
            self.cell(0, 8, "세부 평가 항목", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(3)

            for dim_name, dim_val in dimensions.items():
                score_val = dim_val if isinstance(dim_val, (int, float)) else dim_val.get("score", 0)
                label = _dim_label(dim_name)
                self._draw_score_bar(label, float(score_val), 55)

        if pillar == "geo":
            platform_breakdown = pillar_data.get("platform_breakdown", {})
            if platform_breakdown:
                self.ln(5)
                self._set_font("B", 10)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 8, "AI 플랫폼별 노출 점수", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)
                for p_name, p_data in platform_breakdown.items():
                    ps = p_data.get("geo_score", 0) if isinstance(p_data, dict) else p_data
                    self._draw_score_bar(p_name.capitalize(), float(ps), 55)

        if pillar == "aao":
            industry = pillar_data.get("industry_detected", "")
            if industry and industry != "general":
                industry_labels = {
                    "restaurant": "음식점/요식업", "ecommerce": "이커머스/쇼핑몰",
                    "clinic": "병원/의원", "hotel": "호텔/숙박", "education": "학원/교육",
                    "saas": "소프트웨어(SaaS)", "agency": "에이전시/대행사",
                    "realestate": "부동산", "franchise": "프랜차이즈",
                }
                label = industry_labels.get(industry, industry.title())
                self.ln(5)
                self._set_font("B", 10)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 8, f"감지된 업종: {label}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.ln(5)
        issues = pillar_data.get("issues", [])
        if issues:
            self._set_font("B", 10)
            self.set_text_color(*COLORS["text"])
            self.cell(0, 8, f"발견된 문제 ({len(issues)}건)", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(2)

            for issue in issues[:10]:
                severity = issue.get("severity", "info")
                sev_label = SEVERITY_LABELS_BIZ.get(severity, severity)
                color = SEVERITY_COLORS.get(severity, COLORS["secondary"])
                msg = _translate_issue(issue.get("message", ""))

                self._set_font("", 9)
                self.set_text_color(*color)
                self.cell(5, 6, "", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_fill_color(*color)
                self.set_text_color(255, 255, 255)
                self.cell(28, 6, sev_label, 0, align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 6, f"  {msg[:70]}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def add_roadmap_business(self, data: dict):
        from recommendations import generate_recommendations
        rec_data = generate_recommendations(data)

        self.add_page()
        self._section_title("개선 로드맵")

        industry = rec_data.get("industry", "general")
        if industry != "general":
            industry_labels = {
                "restaurant": "음식점/요식업", "ecommerce": "이커머스/쇼핑몰",
                "clinic": "병원/의원", "hotel": "호텔/숙박", "education": "학원/교육",
                "saas": "소프트웨어(SaaS)", "agency": "에이전시/대행사",
                "realestate": "부동산", "franchise": "프랜차이즈",
            }
            label = industry_labels.get(industry, industry.title())
            self._set_font("", 10)
            self.set_text_color(*COLORS["secondary"])
            self.cell(0, 7, f"업종: {label} | 총 {rec_data['total']}개 개선 항목 도출", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(5)

        if rec_data.get("quick_wins"):
            self._set_font("B", 12)
            self.set_text_color(*COLORS["success"])
            self.cell(0, 8, "바로 실행 가능 (효과 높음, 노력 적음)", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(3)

            for i, r in enumerate(rec_data["quick_wins"][:5], 1):
                r = _translate_rec(r)
                self._set_font("B", 9)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 6, f"{i}. {r['title']}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self._set_font("", 8)
                self.set_text_color(*COLORS["secondary"])
                detail = r["detail"][:120] + ("..." if len(r["detail"]) > 120 else "")
                self.cell(5, 5, "", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.multi_cell(180, 5, detail)
                self._set_font("", 8)
                self.set_text_color(59, 130, 246)
                self.cell(5, 5, "", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                effort = r.get("effort_estimate", "")
                impact = r.get("impact_estimate", "")
                self.cell(0, 5, f"소요 시간: {effort} | 기대 효과: {impact}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(2)

        if rec_data.get("strategic"):
            self.ln(5)
            self._set_font("B", 12)
            self.set_text_color(*COLORS["primary"])
            self.cell(0, 8, "중장기 투자 (효과 높음, 노력 큼)", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(3)

            for i, r in enumerate(rec_data["strategic"][:4], 1):
                r = _translate_rec(r)
                self._set_font("B", 9)
                self.set_text_color(*COLORS["text"])
                self.cell(0, 6, f"{i}. {r['title']}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self._set_font("", 8)
                self.set_text_color(*COLORS["secondary"])
                detail = r["detail"][:120] + ("..." if len(r["detail"]) > 120 else "")
                self.cell(5, 5, "", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.multi_cell(180, 5, detail)
                self.ln(2)

        if rec_data.get("maintenance"):
            self.ln(5)
            self._set_font("B", 12)
            self.set_text_color(*COLORS["secondary"])
            self.cell(0, 8, "유지보수 및 기타 개선", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(3)

            for i, r in enumerate(rec_data["maintenance"][:4], 1):
                r = _translate_rec(r)
                self._set_font("", 9)
                self.set_text_color(*COLORS["text"])
                effort = r.get("effort_estimate", "")
                self.cell(0, 6, f"{i}. {r['title']} ({effort})", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def add_action_plan_business(self, data: dict):
        self.add_page()
        self._section_title("실행 계획")

        all_issues = []
        for pillar in ["seo", "geo", "aao"]:
            pillar_label = PILLAR_LABELS_BIZ.get(pillar, pillar.upper())
            for issue in data.get(pillar, {}).get("issues", []):
                all_issues.append({"pillar": pillar_label, "pillar_key": pillar, **issue})

        severity_order = {"critical": 0, "high": 1, "medium": 2, "warning": 3, "low": 4}
        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 5))

        col_widths = [12, 32, 38, 100]
        headers = ["#", "긴급도", "영역", "조치 사항"]
        self._set_font("B", 9)
        self.set_fill_color(*COLORS["light_bg"])
        self.set_text_color(*COLORS["text"])
        for h, w in zip(headers, col_widths):
            self.cell(w, 7, h, 1, align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.ln()

        self._set_font("", 8)
        for i, issue in enumerate(all_issues[:20], 1):
            severity = issue.get("severity", "low")
            sev_label = SEVERITY_LABELS_BIZ.get(severity, severity)
            msg = _translate_issue(issue.get("message", ""))

            self.set_text_color(*COLORS["text"])
            self.cell(col_widths[0], 6, str(i), 1, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
            color = SEVERITY_COLORS.get(severity, COLORS["secondary"])
            self.set_text_color(*color)
            self.cell(col_widths[1], 6, sev_label, 1, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_text_color(*COLORS["text"])
            self.cell(col_widths[2], 6, issue.get("pillar", ""), 1, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(col_widths[3], 6, msg[:55], 1, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.ln()


def generate_pdf_report(data: dict, output_path: Optional[str] = None, audience: str = "developer") -> str:
    """Generate PDF report from audit data.

    Args:
        data: Audit result data dict
        output_path: Custom output file path
        audience: "developer" for technical report, "business" for plain-language report
    """
    brand = data.get("brand", "Unknown")

    pdf = ThreeOPDF(brand)
    pdf.alias_nb_pages()
    pdf.add_title_page(data)

    if audience == "business":
        pdf.add_overview_business(data)
        for pillar in ["seo", "geo", "aao"]:
            if data.get(pillar):
                pdf.add_pillar_business(pillar, data)
        pdf.add_roadmap_business(data)
        pdf.add_action_plan_business(data)
    else:
        pdf.add_executive_summary(data)
        for pillar in ["seo", "geo", "aao"]:
            if data.get(pillar):
                pdf.add_pillar_section(pillar, data)
        pdf.add_recommendations(data)
        pdf.add_action_plan(data)

    if not output_path:
        reports_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        suffix = "business" if audience == "business" else "full"
        output_path = os.path.join(reports_dir, f"{brand}-{date_str}-{suffix}.pdf")

    pdf.output(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Three-O PDF report generator")
    parser.add_argument("--input", required=True, help="Audit data JSON file")
    parser.add_argument("--output", help="Output PDF path")
    parser.add_argument("--brand", help="Brand name override")
    parser.add_argument("--audience", choices=["developer", "business"], default="developer",
                        help="Report audience: developer (technical) or business (plain language)")
    args = parser.parse_args()

    from pathlib import Path
    data = json.loads(Path(args.input).read_text())

    if args.brand:
        data["brand"] = args.brand

    output_path = generate_pdf_report(data, args.output, args.audience)
    print(f"PDF report saved: {output_path}")


if __name__ == "__main__":
    main()
