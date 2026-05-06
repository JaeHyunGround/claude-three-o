"""Agent conversion funnel readiness script for Three-O platform."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


CONVERSION_WEIGHTS = {
    "entry_point": 0.20,
    "form_accessibility": 0.25,
    "flow_completeness": 0.25,
    "confirmation": 0.15,
    "error_handling": 0.15,
}

FRICTION_POINTS = {
    "captcha": {"impact": "critical", "message": "CAPTCHA blocks agent completion"},
    "login_required": {"impact": "high", "message": "Login required before action"},
    "phone_verify": {"impact": "high", "message": "Phone verification mid-flow"},
    "pdf_only": {"impact": "medium", "message": "Key info in PDF only"},
    "complex_flow": {"impact": "medium", "message": "Complex multi-step flow"},
    "no_guest": {"impact": "high", "message": "No guest checkout/booking option"},
}


def detect_flow_type(html: str) -> str:
    """Detect primary conversion flow type."""
    if re.search(r'(book|reserve|예약|appointment|상담)', html, re.IGNORECASE):
        return "book"
    if re.search(r'(cart|checkout|purchase|buy|구매|장바구니)', html, re.IGNORECASE):
        return "buy"
    if re.search(r'(signup|register|가입|회원)', html, re.IGNORECASE):
        return "signup"
    return "unknown"


def score_entry_point(html: str) -> dict:
    """Score entry point clarity for agent navigation."""
    score = 20.0
    signals = []

    cta_patterns = [
        (r'<(button|a)[^>]*>(.*?(book|reserve|buy|sign up|예약|구매|가입).*?)</\1>', "CTA button found"),
        (r'(potentialAction|OrderAction|ReserveAction)', "Schema.org action defined"),
        (r'<a[^>]*href="[^"]*(?:book|reserve|order|checkout|signup)[^"]*"', "Action URL in navigation"),
    ]

    for pattern, desc in cta_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            score += 20
            signals.append(desc)

    if re.search(r'role="(button|link)"', html, re.IGNORECASE):
        score += 10
        signals.append("ARIA roles on interactive elements")

    if re.search(r'<nav[^>]*>.*?(book|order|예약|구매).*?</nav>', html, re.DOTALL | re.IGNORECASE):
        score += 10
        signals.append("Action in main navigation")

    if not signals:
        signals.append("No clear conversion entry point detected")

    return {"score": min(100, round(score)), "signals": signals}


def score_form_accessibility(html: str) -> dict:
    """Score form parsability for AI agents."""
    score = 20.0
    signals = []

    forms = re.findall(r'<form[^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE)
    if not forms:
        return {"score": 10, "signals": ["No HTML forms found"]}

    score += 15
    signals.append(f"{len(forms)} form(s) found")

    for form_html in forms:
        labels = len(re.findall(r'<label[^>]*>', form_html, re.IGNORECASE))
        inputs = len(re.findall(r'<input[^>]*>', form_html, re.IGNORECASE))

        if labels > 0 and labels >= inputs * 0.5:
            score += 15
            signals.append(f"Labels present ({labels}/{inputs} inputs)")

        typed_inputs = len(re.findall(r'type="(email|tel|number|date|url|text)"', form_html, re.IGNORECASE))
        if typed_inputs > 0:
            score += 10
            signals.append(f"{typed_inputs} semantically typed inputs")

        required = len(re.findall(r'required|aria-required', form_html, re.IGNORECASE))
        if required > 0:
            score += 10
            signals.append(f"{required} required fields marked")

        placeholders = len(re.findall(r'placeholder="', form_html, re.IGNORECASE))
        if placeholders > 0:
            score += 10
            signals.append("Placeholder hints available")

        if re.search(r'(action|method)=', form_html, re.IGNORECASE):
            score += 10

    return {"score": min(100, round(score)), "signals": signals}


def score_flow_completeness(html: str) -> dict:
    """Score whether full flow is completable programmatically."""
    score = 30.0
    signals = []
    frictions = []

    if re.search(r'(recaptcha|hcaptcha|captcha)', html, re.IGNORECASE):
        score -= 30
        frictions.append(FRICTION_POINTS["captcha"])

    if re.search(r'(login|sign in|로그인).*?(required|필수)', html, re.IGNORECASE):
        score -= 15
        frictions.append(FRICTION_POINTS["login_required"])

    if re.search(r'(guest|비회원|비로그인)', html, re.IGNORECASE):
        score += 15
        signals.append("Guest access available")
    else:
        if re.search(r'(회원|member|account)', html, re.IGNORECASE):
            score -= 10
            frictions.append(FRICTION_POINTS["no_guest"])

    steps = len(re.findall(r'(step|단계|STEP)', html, re.IGNORECASE))
    if steps <= 3:
        score += 15
        signals.append(f"Simple flow ({steps} steps)")
    elif steps > 5:
        score -= 10
        frictions.append(FRICTION_POINTS["complex_flow"])

    if re.search(r'(api|ajax|fetch\(|XMLHttpRequest)', html, re.IGNORECASE):
        score += 10
        signals.append("AJAX/API-based submission")

    if re.search(r'\.pdf', html, re.IGNORECASE) and not re.search(r'(online|form|양식)', html, re.IGNORECASE):
        frictions.append(FRICTION_POINTS["pdf_only"])

    return {"score": max(0, min(100, round(score))), "signals": signals, "frictions": frictions}


def score_confirmation(html: str) -> dict:
    """Score confirmation signal clarity."""
    score = 30.0
    signals = []

    if re.search(r'(success|complete|확인|완료|thank)', html, re.IGNORECASE):
        score += 25
        signals.append("Success/completion language found")

    if re.search(r'(confirmation|예약번호|주문번호|reference)', html, re.IGNORECASE):
        score += 25
        signals.append("Confirmation ID pattern detected")

    if re.search(r'(email|이메일|notification|알림)', html, re.IGNORECASE):
        score += 20
        signals.append("Notification mechanism referenced")

    if not signals:
        signals.append("No confirmation signals detected in initial page")

    return {"score": min(100, round(score)), "signals": signals}


def score_error_handling(html: str) -> dict:
    """Score error handling quality."""
    score = 30.0
    signals = []

    if re.search(r'(error|오류|invalid|유효하지)', html, re.IGNORECASE):
        score += 20
        signals.append("Error messaging patterns found")

    if re.search(r'(aria-invalid|aria-errormessage|role="alert")', html, re.IGNORECASE):
        score += 25
        signals.append("ARIA error attributes used")

    if re.search(r'(try again|retry|재시도|다시)', html, re.IGNORECASE):
        score += 15
        signals.append("Retry guidance available")

    if re.search(r'(validation|validate|검증)', html, re.IGNORECASE):
        score += 10
        signals.append("Client-side validation present")

    if not signals:
        signals.append("Limited error handling detected")

    return {"score": min(100, round(score)), "signals": signals}


def analyze_conversion(url: str, flow_type: str = None) -> dict:
    """Full conversion readiness analysis."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    detected_flow = flow_type or detect_flow_type(html)

    dimensions = {
        "entry_point": score_entry_point(html),
        "form_accessibility": score_form_accessibility(html),
        "flow_completeness": score_flow_completeness(html),
        "confirmation": score_confirmation(html),
        "error_handling": score_error_handling(html),
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
        if dim_data["score"] < 30:
            issues.append({"severity": "high", "message": f"Low {dim_name.replace('_', ' ')}: {dim_data['score']}/100"})

    completion_rate = max(0, min(100, round(overall * 0.8)))

    return {
        "success": True,
        "url": url,
        "flow_type": detected_flow,
        "score": overall,
        "estimated_completion_rate": f"{completion_rate}%",
        "dimensions": {k: {"score": v["score"], "signals": v["signals"]} for k, v in dimensions.items()},
        "friction_points": all_frictions,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Agent conversion funnel analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--flow", choices=["book", "buy", "signup"], help="Conversion flow type")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_conversion(args.url, args.flow)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Conversion Score: {result['score']}/100")
            print(f"Flow Type: {result['flow_type']} | Est. Completion: {result['estimated_completion_rate']}")
            print(f"\nDimension Scores:")
            for dim, data in result["dimensions"].items():
                bar = "█" * int(data["score"] / 10) + "░" * (10 - int(data["score"] / 10))
                print(f"  {dim.replace('_', ' ').title():25s} {bar} {data['score']}")
            if result["friction_points"]:
                print(f"\nFriction Points:")
                for fp in result["friction_points"]:
                    print(f"  [{fp['impact'].upper()}] {fp['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
