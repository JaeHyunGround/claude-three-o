"""Agent conversion funnel readiness script for Three-O platform.

Scores conversion funnel across six dimensions:
- CTA Quality: visibility, specificity, action schema, urgency signals
- Form Accessibility: semantic inputs, labels, autocomplete, field efficiency
- Flow Completeness: payment path depth, guest access, step count, friction
- Mobile Conversion: viewport, touch targets, click-to-call, responsive forms
- Deep Link: app links, direct URLs, API endpoints, parameter navigation
- Confirmation & Error: success signals, confirmation IDs, ARIA errors, retry
"""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


CONVERSION_WEIGHTS = {
    "cta_quality": 0.20,
    "form_accessibility": 0.20,
    "flow_completeness": 0.20,
    "mobile_conversion": 0.15,
    "deep_link": 0.10,
    "confirmation_error": 0.15,
}

FRICTION_POINTS = {
    "captcha": {"impact": "critical", "message": "CAPTCHA가 에이전트 전환 완료를 차단"},
    "login_required": {"impact": "high", "message": "액션 전 로그인 필수"},
    "phone_verify": {"impact": "high", "message": "전환 중 전화 인증 필요"},
    "pdf_only": {"impact": "medium", "message": "핵심 정보가 PDF에만 존재"},
    "complex_flow": {"impact": "medium", "message": "5단계 이상 복잡한 플로우"},
    "no_guest": {"impact": "high", "message": "비회원 결제/예약 불가"},
    "no_price": {"impact": "medium", "message": "가격 정보 미노출"},
    "iframe_form": {"impact": "medium", "message": "iframe 내 폼 — 에이전트 접근 제한"},
}

CTA_QUALITY_SIGNALS = {
    "specific_action": [
        r'(?:예약하기|지금\s*예약|바로\s*구매|장바구니\s*담기|신청하기|상담\s*신청)',
        r'(?:book now|reserve|add to cart|buy now|sign up|get started|apply now)',
    ],
    "generic_action": [
        r'(?:클릭|더보기|자세히|여기를|click here|learn more|read more|submit)',
    ],
    "urgency": [
        r'(?:한정|마감|오늘만|특가|할인|무료|즉시|지금)',
        r'(?:limited|deadline|today only|sale|free|instant|now)',
    ],
    "schema_action": [
        r'(?:potentialAction|OrderAction|ReserveAction|BuyAction|SubscribeAction)',
    ],
}


def extract_text_content(html: str) -> str:
    """Strip HTML tags and extract text content."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_flow_type(html: str) -> str:
    """Detect primary conversion flow type."""
    patterns = [
        ("book", r'(?:book|reserve|예약|appointment|상담\s*신청|진료\s*예약)'),
        ("buy", r'(?:cart|checkout|purchase|buy|구매|장바구니|결제)'),
        ("signup", r'(?:signup|register|가입|회원|subscribe|구독)'),
        ("inquiry", r'(?:문의|상담|contact|inquiry|견적)'),
        ("download", r'(?:download|다운로드|받기|설치)'),
    ]
    for flow, pattern in patterns:
        if re.search(pattern, html, re.IGNORECASE):
            return flow
    return "unknown"


def detect_industry(html: str) -> str:
    """Detect industry from page content for weight adjustment."""
    text = extract_text_content(html).lower()
    patterns = [
        ("restaurant", r'(?:메뉴|음식|맛집|레스토랑|카페|배달|menu|restaurant|cafe)'),
        ("ecommerce", r'(?:상품|배송|장바구니|주문|카트|product|shipping|cart)'),
        ("clinic", r'(?:진료|병원|클리닉|의원|치과|의사|clinic|hospital|doctor)'),
        ("hotel", r'(?:객실|숙박|체크인|호텔|리조트|room|hotel|resort|check-in)'),
        ("education", r'(?:수강|강좌|학원|교육|수업|course|class|academy|lesson)'),
        ("saas", r'(?:요금제|플랜|구독|trial|pricing|plan|subscribe|SaaS)'),
    ]
    for industry, pattern in patterns:
        if re.search(pattern, text):
            return industry
    return "general"


def score_cta_quality(html: str) -> dict:
    """Score CTA quality — specificity, visibility, action schema, urgency."""
    score = 10.0
    details = {}

    buttons = re.findall(
        r'<(?:button|a)[^>]*(?:class="[^"]*(?:btn|button|cta)[^"]*"|role="button")[^>]*>(.*?)</(?:button|a)>',
        html, re.DOTALL | re.IGNORECASE
    )
    generic_buttons = re.findall(
        r'<(?:button|a)[^>]*>(.*?)</(?:button|a)>',
        html, re.DOTALL | re.IGNORECASE
    )
    all_buttons = buttons or generic_buttons
    details["cta_count"] = len(all_buttons)

    if all_buttons:
        score += 10

    specific_count = 0
    generic_count = 0
    for btn_text in all_buttons:
        btn_clean = re.sub(r'<[^>]+>', '', btn_text).strip()
        if not btn_clean:
            continue
        is_specific = any(
            re.search(p, btn_clean, re.IGNORECASE)
            for p in CTA_QUALITY_SIGNALS["specific_action"]
        )
        is_generic = any(
            re.search(p, btn_clean, re.IGNORECASE)
            for p in CTA_QUALITY_SIGNALS["generic_action"]
        )
        if is_specific:
            specific_count += 1
        elif is_generic:
            generic_count += 1

    details["specific_ctas"] = specific_count
    details["generic_ctas"] = generic_count

    if specific_count > 0:
        score += 25
    elif generic_count > 0:
        score += 10

    has_schema_action = any(
        re.search(p, html, re.IGNORECASE)
        for p in CTA_QUALITY_SIGNALS["schema_action"]
    )
    details["schema_action"] = has_schema_action
    if has_schema_action:
        score += 20

    action_urls = re.findall(
        r'<a[^>]*href="[^"]*(?:book|reserve|order|checkout|signup|buy|cart|예약|구매|신청)[^"]*"',
        html, re.IGNORECASE
    )
    details["action_urls"] = len(action_urls)
    if action_urls:
        score += 10

    has_urgency = any(
        re.search(p, html, re.IGNORECASE)
        for p in CTA_QUALITY_SIGNALS["urgency"]
    )
    details["urgency_signals"] = has_urgency
    if has_urgency:
        score += 5

    has_aria_role = bool(re.search(r'role="(?:button|link)"', html, re.IGNORECASE))
    details["aria_roles"] = has_aria_role
    if has_aria_role:
        score += 10

    has_nav_action = bool(re.search(
        r'<nav[^>]*>.*?(?:book|order|예약|구매|신청|상담).*?</nav>',
        html, re.DOTALL | re.IGNORECASE
    ))
    details["nav_action"] = has_nav_action
    if has_nav_action:
        score += 10

    return {"score": round(min(100.0, score), 1), "details": details}


def score_form_accessibility(html: str) -> dict:
    """Score form parsability for AI agents with quality assessment."""
    score = 10.0
    details = {}

    forms = re.findall(r'<form[^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE)
    details["form_count"] = len(forms)

    if not forms:
        has_iframe_form = bool(re.search(r'<iframe[^>]*(?:form|book|reserve|signup)', html, re.IGNORECASE))
        details["iframe_form"] = has_iframe_form
        return {"score": 5.0 if has_iframe_form else 0.0, "details": details}

    score += 10

    total_inputs = 0
    total_labels = 0
    total_typed = 0
    total_required = 0
    total_autocomplete = 0
    total_placeholders = 0
    has_action = False
    has_method = False

    for form_html in forms:
        inputs = re.findall(r'<input[^>]*>', form_html, re.IGNORECASE)
        labels = len(re.findall(r'<label[^>]*>', form_html, re.IGNORECASE))
        total_inputs += len(inputs)
        total_labels += labels

        for inp in inputs:
            if re.search(r'type="(email|tel|number|date|url|time|datetime-local|month|week)"', inp, re.IGNORECASE):
                total_typed += 1
            if re.search(r'(?:required|aria-required="true")', inp, re.IGNORECASE):
                total_required += 1
            if re.search(r'autocomplete="', inp, re.IGNORECASE):
                total_autocomplete += 1
            if re.search(r'placeholder="', inp, re.IGNORECASE):
                total_placeholders += 1

        selects = len(re.findall(r'<select[^>]*>', form_html, re.IGNORECASE))
        textareas = len(re.findall(r'<textarea[^>]*>', form_html, re.IGNORECASE))
        total_inputs += selects + textareas

        if re.search(r'action="', form_html, re.IGNORECASE):
            has_action = True
        if re.search(r'method="', form_html, re.IGNORECASE):
            has_method = True

    details["total_inputs"] = total_inputs
    details["total_labels"] = total_labels
    details["typed_inputs"] = total_typed
    details["required_marked"] = total_required
    details["autocomplete_attrs"] = total_autocomplete
    details["placeholders"] = total_placeholders

    if total_labels > 0 and total_inputs > 0:
        label_ratio = total_labels / total_inputs
        details["label_ratio"] = round(label_ratio, 2)
        if label_ratio >= 0.8:
            score += 15
        elif label_ratio >= 0.5:
            score += 8

    if total_typed > 0:
        score += min(15, total_typed * 4)

    if total_required > 0:
        score += 8

    if total_autocomplete > 0:
        score += min(12, total_autocomplete * 4)

    if total_placeholders > 0:
        score += 5

    if has_action and has_method:
        score += 10

    if total_inputs > 0 and total_inputs <= 5:
        score += 10
        details["field_efficiency"] = "optimal"
    elif total_inputs <= 10:
        score += 5
        details["field_efficiency"] = "acceptable"
    elif total_inputs > 10:
        details["field_efficiency"] = "heavy"

    fieldsets = len(re.findall(r'<fieldset', html, re.IGNORECASE))
    if fieldsets > 0:
        score += 5
        details["fieldsets"] = fieldsets

    return {"score": round(min(100.0, score), 1), "details": details}


def score_flow_completeness(html: str) -> dict:
    """Score flow completeness with payment path depth and friction detection."""
    score = 20.0
    details = {}
    frictions = []

    if re.search(r'(?:recaptcha|hcaptcha|captcha)', html, re.IGNORECASE):
        score -= 25
        frictions.append(FRICTION_POINTS["captcha"])
        details["captcha"] = True

    if re.search(r'(?:login|sign in|로그인).*?(?:required|필수)', html, re.IGNORECASE):
        score -= 15
        frictions.append(FRICTION_POINTS["login_required"])
        details["login_required"] = True

    has_guest = bool(re.search(r'(?:guest|비회원|비로그인|게스트)', html, re.IGNORECASE))
    details["guest_access"] = has_guest
    if has_guest:
        score += 15
    elif re.search(r'(?:회원|member|account)', html, re.IGNORECASE):
        score -= 10
        frictions.append(FRICTION_POINTS["no_guest"])

    steps = len(re.findall(r'(?:step|단계|STEP)\s*\d', html, re.IGNORECASE))
    details["detected_steps"] = steps
    if steps == 0 or steps <= 3:
        score += 12
    elif steps > 5:
        score -= 10
        frictions.append(FRICTION_POINTS["complex_flow"])

    payment_signals = {
        "price_visible": bool(re.search(r'(?:₩|원|price|가격|요금)\s*[\d,]+', html, re.IGNORECASE)),
        "payment_methods": bool(re.search(
            r'(?:카드|신용카드|네이버페이|카카오페이|토스|visa|mastercard|paypal|credit card|apple pay|google pay)',
            html, re.IGNORECASE
        )),
        "secure_checkout": bool(re.search(r'(?:ssl|secure|보안|안전한\s*결제|https)', html, re.IGNORECASE)),
        "refund_policy": bool(re.search(r'(?:환불|취소|refund|cancel|return)', html, re.IGNORECASE)),
    }
    details["payment"] = payment_signals

    if payment_signals["price_visible"]:
        score += 10
    else:
        text = extract_text_content(html)
        if re.search(r'(?:구매|결제|checkout|buy)', text, re.IGNORECASE):
            frictions.append(FRICTION_POINTS["no_price"])

    if payment_signals["payment_methods"]:
        score += 8
    if payment_signals["secure_checkout"]:
        score += 5
    if payment_signals["refund_policy"]:
        score += 5

    if re.search(r'(?:api|ajax|fetch\(|XMLHttpRequest|axios)', html, re.IGNORECASE):
        score += 8
        details["api_submission"] = True

    if re.search(r'\.pdf', html, re.IGNORECASE) and not re.search(r'(?:online|form|양식)', html, re.IGNORECASE):
        frictions.append(FRICTION_POINTS["pdf_only"])

    if re.search(r'<iframe[^>]*(?:form|book|payment)', html, re.IGNORECASE):
        frictions.append(FRICTION_POINTS["iframe_form"])

    return {"score": round(max(0.0, min(100.0, score)), 1), "details": details, "frictions": frictions}


def score_mobile_conversion(html: str) -> dict:
    """Score mobile conversion optimization."""
    score = 10.0
    details = {}

    has_viewport = bool(re.search(r'<meta[^>]*name="viewport"', html, re.IGNORECASE))
    details["viewport"] = has_viewport
    if has_viewport:
        score += 15

    has_responsive = bool(re.search(r'@media[^{]*(?:max-width|min-width)', html, re.IGNORECASE))
    has_responsive_class = bool(re.search(r'class="[^"]*(?:col-(?:sm|md|lg|xs)|mobile|responsive)', html, re.IGNORECASE))
    details["responsive"] = has_responsive or has_responsive_class
    if has_responsive or has_responsive_class:
        score += 10

    click_to_call = bool(re.search(r'href="tel:', html, re.IGNORECASE))
    details["click_to_call"] = click_to_call
    if click_to_call:
        score += 15

    click_to_sms = bool(re.search(r'href="sms:', html, re.IGNORECASE))
    details["click_to_sms"] = click_to_sms
    if click_to_sms:
        score += 5

    click_to_map = bool(re.search(
        r'(?:href="(?:https?://)?(?:maps\.google|map\.naver|map\.kakao|maps\.apple))',
        html, re.IGNORECASE
    ))
    details["click_to_map"] = click_to_map
    if click_to_map:
        score += 10

    touch_friendly = bool(re.search(
        r'(?:touch-action|tap-highlight|-webkit-tap|min-height:\s*4[0-9]px|padding:\s*1[2-9]px)',
        html, re.IGNORECASE
    ))
    details["touch_friendly"] = touch_friendly
    if touch_friendly:
        score += 10

    mobile_cta = bool(re.search(
        r'(?:class="[^"]*(?:sticky|fixed|bottom)[^"]*"[^>]*>.*?(?:button|예약|구매|신청))',
        html, re.DOTALL | re.IGNORECASE
    ))
    details["mobile_sticky_cta"] = mobile_cta
    if mobile_cta:
        score += 10

    mobile_input = bool(re.search(r'inputmode="(?:numeric|tel|email|decimal|url)"', html, re.IGNORECASE))
    details["mobile_input_modes"] = mobile_input
    if mobile_input:
        score += 8

    sns_login = bool(re.search(
        r'(?:카카오\s*로그인|네이버\s*로그인|kakao.*?login|naver.*?login|소셜\s*로그인|social\s*login)',
        html, re.IGNORECASE
    ))
    details["sns_login"] = sns_login
    if sns_login:
        score += 7

    no_pinch = bool(re.search(r'user-scalable\s*=\s*no', html, re.IGNORECASE))
    details["blocks_zoom"] = no_pinch
    if no_pinch:
        score -= 5

    return {"score": round(max(0.0, min(100.0, score)), 1), "details": details}


def score_deep_link(html: str) -> dict:
    """Score deep link and direct navigation capability."""
    score = 10.0
    details = {}

    ios_universal = bool(re.search(r'apple-app-site-association|apple-itunes-app', html, re.IGNORECASE))
    details["ios_universal_link"] = ios_universal
    if ios_universal:
        score += 15

    android_app_link = bool(re.search(r'android-app://|intent://|package=', html, re.IGNORECASE))
    details["android_app_link"] = android_app_link
    if android_app_link:
        score += 15

    app_scheme = bool(re.search(r'href="(?:kakao|naver|line|toss)(?:talk)?://', html, re.IGNORECASE))
    details["custom_scheme"] = app_scheme
    if app_scheme:
        score += 10

    canonical = bool(re.search(r'<link[^>]*rel="canonical"[^>]*href="[^"]*"', html, re.IGNORECASE))
    details["canonical"] = canonical
    if canonical:
        score += 10

    api_endpoints = re.findall(r'(?:/api/|/v\d+/|\.json|/rest/)', html, re.IGNORECASE)
    details["api_endpoints"] = len(api_endpoints) > 0
    if api_endpoints:
        score += 10

    og_url = bool(re.search(r'<meta[^>]*property="og:url"[^>]*content="[^"]*"', html, re.IGNORECASE))
    details["og_url"] = og_url
    if og_url:
        score += 8

    direct_action_urls = re.findall(
        r'href="(/[^"]*(?:book|reserve|order|buy|signup|예약|구매|신청)[^"]*)"',
        html, re.IGNORECASE
    )
    details["direct_action_paths"] = len(direct_action_urls)
    if direct_action_urls:
        score += 12

    share_links = bool(re.search(
        r'(?:share|공유|copy.*?link|링크\s*복사)',
        html, re.IGNORECASE
    ))
    details["share_mechanism"] = share_links
    if share_links:
        score += 5

    hash_nav = len(re.findall(r'href="#[a-zA-Z][\w-]*"', html))
    details["hash_navigation"] = hash_nav > 0
    if hash_nav >= 3:
        score += 5

    return {"score": round(min(100.0, score), 1), "details": details}


def score_confirmation_error(html: str) -> dict:
    """Score confirmation signals and error handling quality."""
    score = 10.0
    details = {}

    success_patterns = [
        (r'(?:success|complete|확인|완료|감사합니다|thank)', "success_language"),
        (r'(?:confirmation|예약번호|주문번호|reference|접수번호)', "confirmation_id"),
        (r'(?:email|이메일|notification|알림|문자|SMS)', "notification"),
    ]
    for pattern, key in success_patterns:
        found = bool(re.search(pattern, html, re.IGNORECASE))
        details[key] = found
        if found:
            score += 10

    error_patterns = [
        (r'(?:error|오류|invalid|유효하지|잘못된)', "error_messages", 8),
        (r'(?:aria-invalid|aria-errormessage|role="alert")', "aria_errors", 12),
        (r'(?:try again|retry|재시도|다시\s*시도)', "retry_guidance", 8),
        (r'(?:validation|validate|검증|pattern=")', "client_validation", 8),
    ]
    for pattern, key, points in error_patterns:
        found = bool(re.search(pattern, html, re.IGNORECASE))
        details[key] = found
        if found:
            score += points

    http_error = bool(re.search(r'(?:404|500|503|에러\s*페이지|error\s*page)', html, re.IGNORECASE))
    details["error_page_handling"] = http_error
    if http_error:
        score += 7

    loading_state = bool(re.search(r'(?:loading|spinner|로딩|처리\s*중|submitting)', html, re.IGNORECASE))
    details["loading_state"] = loading_state
    if loading_state:
        score += 7

    return {"score": round(min(100.0, score), 1), "details": details}


def analyze_conversion(url: str, flow_type: str = None) -> dict:
    """Full conversion readiness analysis."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    return analyze_conversion_html(result["html"], url, flow_type)


def analyze_conversion_html(html: str, url: str = "", flow_type: str = None) -> dict:
    """Run conversion analysis on raw HTML."""
    detected_flow = flow_type or detect_flow_type(html)
    detected_industry = detect_industry(html)

    dimensions = {
        "cta_quality": score_cta_quality(html),
        "form_accessibility": score_form_accessibility(html),
        "flow_completeness": score_flow_completeness(html),
        "mobile_conversion": score_mobile_conversion(html),
        "deep_link": score_deep_link(html),
        "confirmation_error": score_confirmation_error(html),
    }

    overall = round(sum(
        dimensions[k]["score"] * CONVERSION_WEIGHTS[k]
        for k in CONVERSION_WEIGHTS
    ), 1)

    all_frictions = []
    for dim_data in dimensions.values():
        all_frictions.extend(dim_data.get("frictions", []))

    issues = []
    for friction in all_frictions:
        issues.append({"severity": friction["impact"], "message": friction["message"]})

    for dim_name, dim_data in dimensions.items():
        if dim_data["score"] < 20:
            issues.append({
                "severity": "high",
                "dimension": dim_name,
                "message": f"{dim_name.replace('_', ' ').title()} 매우 약함 ({dim_data['score']:.0f}/100)",
            })
        elif dim_data["score"] < 40:
            issues.append({
                "severity": "medium",
                "dimension": dim_name,
                "message": f"{dim_name.replace('_', ' ').title()} 보강 필요 ({dim_data['score']:.0f}/100)",
            })

    issues.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.get("severity", "low"), 4))

    weakest = min(CONVERSION_WEIGHTS, key=lambda k: dimensions[k]["score"])
    strongest = max(CONVERSION_WEIGHTS, key=lambda k: dimensions[k]["score"])

    completion_rate = max(0, min(100, round(overall * 0.8)))

    return {
        "success": True,
        "url": url,
        "flow_type": detected_flow,
        "industry": detected_industry,
        "score": overall,
        "estimated_completion_rate": f"{completion_rate}%",
        "dimensions": {k: v["score"] for k, v in dimensions.items()},
        "dimension_details": {k: v.get("details", {}) for k, v in dimensions.items()},
        "weakest_dimension": weakest,
        "strongest_dimension": strongest,
        "friction_points": all_frictions,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Agent conversion funnel analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--flow", choices=["book", "buy", "signup", "inquiry", "download"],
                        help="Conversion flow type")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_conversion(args.url, args.flow)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Conversion Score: {result['score']}/100")
            print(f"Flow: {result['flow_type']} | Industry: {result['industry']} | Est. Completion: {result['estimated_completion_rate']}")
            print(f"Weakest: {result['weakest_dimension']} | Strongest: {result['strongest_dimension']}")
            print(f"\nDimensions:")
            for dim, score in result["dimensions"].items():
                bar = "#" * int(score / 10) + "." * (10 - int(score / 10))
                print(f"  {dim.replace('_', ' ').title():25s} [{bar}] {score:.0f}")
            if result["friction_points"]:
                print(f"\nFriction Points ({len(result['friction_points'])}):")
                for fp in result["friction_points"]:
                    print(f"  [{fp['impact'].upper()}] {fp['message']}")
            if result["issues"]:
                print(f"\nIssues ({len(result['issues'])}):")
                for issue in result["issues"]:
                    print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
