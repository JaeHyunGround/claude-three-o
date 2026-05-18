"""AAO product feed validation — 6-dimension quality scoring.

Dimensions (weights):
  1. data_quality       (0.25) — field value quality: title, description, URLs, format
  2. field_completeness (0.20) — required/optional field coverage per platform
  3. feed_freshness     (0.15) — date signals, update indicators, staleness detection
  4. pricing_accuracy   (0.15) — currency format, sale price consistency, price validity
  5. media_quality      (0.10) — image URL validity, multiple images, format signals
  6. platform_compliance(0.15) — Google Merchant / Naver Shopping specific requirements
"""

import argparse
import json
import re
from datetime import datetime
from urllib.parse import urlparse

from validate_url import validate_url
from fetch_page import fetch_page


CURRENT_YEAR = datetime.now().year

DIMENSION_WEIGHTS = {
    "data_quality": 0.25,
    "field_completeness": 0.20,
    "feed_freshness": 0.15,
    "pricing_accuracy": 0.15,
    "media_quality": 0.10,
    "platform_compliance": 0.15,
}

GOOGLE_REQUIRED = ["id", "title", "description", "link", "image_link",
                   "price", "availability", "condition", "brand"]

GOOGLE_RECOMMENDED = ["gtin", "mpn", "google_product_category", "product_type",
                      "sale_price", "shipping", "color", "size", "material",
                      "custom_label_0", "item_group_id"]

NAVER_REQUIRED = ["id", "title", "price_pc", "link", "image_link",
                  "category1", "shipping"]

NAVER_RECOMMENDED = ["category2", "category3", "category4", "event_words",
                     "import_flag", "manufacture", "brand", "model_no",
                     "origin", "card_event"]


def parse_product_feed(content: str) -> dict:
    """Parse product feed XML content."""
    items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL | re.IGNORECASE)
    if not items:
        items = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL | re.IGNORECASE)
    if not items:
        items = re.findall(r'<product>(.*?)</product>', content, re.DOTALL | re.IGNORECASE)

    products = []
    for item in items[:100]:
        product = {}
        fields = re.findall(r'<(g:)?(\w+)>(.*?)</\1?\2>', item, re.DOTALL)
        for _, field_name, value in fields:
            product[field_name.lower()] = value.strip()

        if not product:
            simple_fields = re.findall(r'<(\w+)>(.*?)</\1>', item, re.DOTALL)
            for name, value in simple_fields:
                product[name.lower()] = value.strip()

        if product:
            products.append(product)

    return {
        "total_items": len(items),
        "parsed_sample": len(products),
        "products": products[:20],
    }


# ---------------------------------------------------------------------------
# 6-dimension scoring
# ---------------------------------------------------------------------------

def score_data_quality(products: list) -> dict:
    """Score field value quality across products (0-100)."""
    if not products:
        return {"score": 0.0, "details": {"checked": 0}, "issues": []}

    score = 0.0
    issues = []
    sample = products[:20]
    n = len(sample)

    titles = [p.get("title", "") for p in sample]
    valid_titles = sum(1 for t in titles if t and 10 <= len(t) <= 150)
    short_titles = sum(1 for t in titles if t and len(t) < 10)
    sum(1 for t in titles if t and len(t) > 150)
    no_titles = sum(1 for t in titles if not t)

    title_rate = valid_titles / n
    if title_rate >= 0.9:
        score += 20
    elif title_rate >= 0.7:
        score += 14
    elif title_rate >= 0.5:
        score += 8
    elif valid_titles > 0:
        score += 4

    if short_titles > 0:
        issues.append(f"{short_titles} products with short titles (<10 chars)")
    if no_titles > 0:
        issues.append(f"{no_titles} products missing titles")

    unique_titles = len(set(t.lower() for t in titles if t))
    if n > 1 and unique_titles < n * 0.8:
        score -= 5
        issues.append(f"title uniqueness low ({unique_titles}/{n})")

    descs = [p.get("description", "") for p in sample]
    valid_descs = sum(1 for d in descs if d and len(d) >= 30)
    desc_rate = valid_descs / n
    if desc_rate >= 0.9:
        score += 20
    elif desc_rate >= 0.7:
        score += 14
    elif desc_rate >= 0.4:
        score += 8
    elif valid_descs > 0:
        score += 4

    missing_descs = sum(1 for d in descs if not d)
    if missing_descs > 0:
        issues.append(f"{missing_descs} products missing descriptions")

    links = [p.get("link", "") for p in sample]
    valid_links = sum(1 for lk in links if lk and lk.startswith("http"))
    https_links = sum(1 for lk in links if lk and lk.startswith("https"))
    link_rate = valid_links / n
    if link_rate >= 0.95:
        score += 15
    elif link_rate >= 0.8:
        score += 10
    elif valid_links > 0:
        score += 5
    if valid_links > 0 and https_links / valid_links >= 0.9:
        score += 5

    invalid_links = n - valid_links
    if invalid_links > 0:
        issues.append(f"{invalid_links} products with invalid/missing links")

    ids = [p.get("id", "") for p in sample]
    valid_ids = sum(1 for i in ids if i and len(i) > 0)
    unique_ids = len(set(i for i in ids if i))
    if valid_ids == n and unique_ids == n:
        score += 15
    elif valid_ids == n:
        score += 10
        if unique_ids < n:
            issues.append(f"duplicate IDs detected ({n - unique_ids})")
    elif valid_ids > 0:
        score += 5

    html_in_fields = sum(1 for p in sample if any(re.search(r'<[^>]+>', str(v)) for v in p.values()))
    if html_in_fields > 0:
        score -= 5
        issues.append(f"HTML markup found in {html_in_fields} products")

    empty_fields_avg = sum(sum(1 for v in p.values() if not v) for p in sample) / n if n > 0 else 0
    if empty_fields_avg > 3:
        score -= 5
        issues.append(f"high empty field rate (avg {empty_fields_avg:.1f} per product)")

    if n > 0:
        field_counts = [len(p) for p in sample]
        avg_fields = sum(field_counts) / n
        if avg_fields >= 12:
            score += 10
        elif avg_fields >= 8:
            score += 7
        elif avg_fields >= 5:
            score += 4

    score = round(max(0, min(100, score)), 1)
    return {"score": score, "details": {"checked": n, "valid_titles": valid_titles, "valid_descs": valid_descs, "valid_links": valid_links}, "issues": issues}


def score_field_completeness(products: list, platform: str = "google") -> dict:
    """Score required/optional field coverage per platform (0-100)."""
    required = GOOGLE_REQUIRED if platform == "google" else NAVER_REQUIRED
    recommended = GOOGLE_RECOMMENDED if platform == "google" else NAVER_RECOMMENDED

    if not products:
        return {"score": 0.0, "details": {"platform": platform, "missing_required": required}, "coverage": {}}

    n = len(products[:20])
    sample = products[:20]

    req_coverage = {}
    for field in required:
        present = sum(1 for p in sample if p.get(field))
        req_coverage[field] = round(present / n * 100)

    avg_req = round(sum(req_coverage.values()) / max(len(req_coverage), 1))

    opt_coverage = {}
    for field in recommended:
        present = sum(1 for p in sample if p.get(field))
        opt_coverage[field] = round(present / n * 100)

    avg_opt = round(sum(opt_coverage.values()) / max(len(opt_coverage), 1))

    score = avg_req * 0.75 + avg_opt * 0.25

    missing_required = [f for f, pct in req_coverage.items() if pct < 50]
    missing_optional = [f for f, pct in opt_coverage.items() if pct < 20]

    all_coverage = {**req_coverage, **opt_coverage}

    score = round(min(100, score), 1)
    return {
        "score": score,
        "details": {
            "platform": platform,
            "required_avg": avg_req,
            "optional_avg": avg_opt,
            "missing_required": missing_required,
            "missing_optional": missing_optional[:5],
        },
        "coverage": all_coverage,
    }


def score_feed_freshness(content: str) -> dict:
    """Score feed freshness indicators (0-100)."""
    score = 0.0
    signals = []

    current = CURRENT_YEAR
    recent_dates = re.findall(rf'{current}-\d{{2}}-\d{{2}}', content)
    last_year_dates = re.findall(rf'{current - 1}-\d{{2}}-\d{{2}}', content)
    old_dates = re.findall(rf'{current - 2}-\d{{2}}-\d{{2}}', content)

    if recent_dates:
        score += 30
        signals.append(f"current year dates ({len(recent_dates)} found, e.g. {recent_dates[0]})")
    elif last_year_dates:
        score += 15
        signals.append(f"last year dates ({len(last_year_dates)} found)")
    elif old_dates:
        score += 5
        signals.append(f"dated {current - 2} (aging content)")

    if re.search(r'<lastBuildDate>[^<]+</lastBuildDate>', content, re.IGNORECASE):
        score += 15
        signals.append("lastBuildDate present")

    if re.search(r'<pubDate>[^<]+</pubDate>', content, re.IGNORECASE):
        score += 10
        signals.append("pubDate present")

    if re.search(r'<updated>[^<]+</updated>', content, re.IGNORECASE):
        score += 10
        signals.append("updated tag present")

    if re.search(r'<modified>[^<]+</modified>', content, re.IGNORECASE):
        score += 5
        signals.append("modified tag present")

    ttl_match = re.search(r'<ttl>(\d+)</ttl>', content, re.IGNORECASE)
    if ttl_match:
        ttl_val = int(ttl_match.group(1))
        if ttl_val <= 60:
            score += 15
            signals.append(f"fast refresh (TTL={ttl_val}min)")
        elif ttl_val <= 1440:
            score += 10
            signals.append(f"daily refresh (TTL={ttl_val}min)")
        else:
            score += 5
            signals.append(f"slow refresh (TTL={ttl_val}min)")

    avail_changes = len(re.findall(r'<g?:?availability>[^<]*</g?:?availability>', content, re.IGNORECASE))
    if avail_changes > 0:
        score += 10
        signals.append(f"availability status ({avail_changes} items)")

    sale_prices = len(re.findall(r'<g?:?sale_price>[^<]*</g?:?sale_price>', content, re.IGNORECASE))
    if sale_prices > 0:
        score += 5
        signals.append(f"sale pricing ({sale_prices} items)")

    score = round(min(100, score), 1)
    return {"score": score, "signals": signals}


def score_pricing_accuracy(products: list) -> dict:
    """Score pricing quality and consistency (0-100)."""
    if not products:
        return {"score": 0.0, "details": {}, "issues": []}

    score = 0.0
    issues = []
    sample = products[:20]
    n = len(sample)

    prices_found = 0
    valid_format = 0
    has_currency = 0
    for p in sample:
        price_str = p.get("price") or p.get("price_pc") or p.get("sale_price") or ""
        if not price_str:
            continue
        prices_found += 1

        if re.search(r'\d', str(price_str)):
            valid_format += 1

        if re.search(r'(KRW|USD|EUR|JPY|원|\$|€|¥)', str(price_str), re.IGNORECASE):
            has_currency += 1

    if prices_found == 0:
        issues.append("no pricing data found")
        return {"score": 0.0, "details": {"prices_found": 0}, "issues": issues}

    price_rate = prices_found / n
    if price_rate >= 0.95:
        score += 25
    elif price_rate >= 0.8:
        score += 18
    elif price_rate >= 0.5:
        score += 10
    else:
        score += 5

    format_rate = valid_format / prices_found if prices_found > 0 else 0
    if format_rate >= 0.95:
        score += 20
    elif format_rate >= 0.8:
        score += 12
    elif format_rate > 0:
        score += 5

    currency_rate = has_currency / prices_found if prices_found > 0 else 0
    if currency_rate >= 0.9:
        score += 20
        if currency_rate < 1.0:
            issues.append(f"inconsistent currency format ({has_currency}/{prices_found})")
    elif currency_rate >= 0.5:
        score += 10
    elif currency_rate > 0:
        score += 5

    sale_count = 0
    sale_valid = 0
    for p in sample:
        sale = p.get("sale_price")
        regular = p.get("price")
        if sale and regular:
            sale_count += 1
            try:
                sale_num = float(re.sub(r'[^\d.]', '', str(sale)))
                reg_num = float(re.sub(r'[^\d.]', '', str(regular)))
                if 0 < sale_num < reg_num:
                    sale_valid += 1
                else:
                    issues.append("sale price >= regular price in product")
            except (ValueError, ZeroDivisionError):
                pass

    if sale_count > 0:
        if sale_valid == sale_count:
            score += 15
        elif sale_valid > 0:
            score += 8
            issues.append(f"some sale prices invalid ({sale_count - sale_valid}/{sale_count})")

    zero_prices = sum(1 for p in sample if p.get("price") and re.match(r'^0+\.?0*$', re.sub(r'[^\d.]', '', str(p.get("price", "0")))))
    if zero_prices > 0:
        score -= 10
        issues.append(f"{zero_prices} products with zero price")

    effective_dates = sum(1 for p in sample if p.get("sale_price_effective_date"))
    if effective_dates > 0:
        score += 10

    shipping = sum(1 for p in sample if p.get("shipping") or p.get("shipping_weight"))
    if shipping > 0:
        score += 10

    score = round(max(0, min(100, score)), 1)
    return {
        "score": score,
        "details": {
            "prices_found": prices_found,
            "valid_format": valid_format,
            "has_currency": has_currency,
            "sale_count": sale_count,
            "sale_valid": sale_valid,
        },
        "issues": issues,
    }


def score_media_quality(products: list) -> dict:
    """Score image/media quality in feed (0-100)."""
    if not products:
        return {"score": 0.0, "details": {}, "signals": []}

    score = 0.0
    signals = []
    sample = products[:20]
    n = len(sample)

    img_found = 0
    https_imgs = 0
    valid_format = 0
    for p in sample:
        img = p.get("image_link") or p.get("image") or ""
        if img:
            img_found += 1
            if img.startswith("https"):
                https_imgs += 1
            if re.search(r'\.(jpg|jpeg|png|webp|gif|avif)', img, re.IGNORECASE):
                valid_format += 1

    if img_found == 0:
        signals.append("no images found")
        return {"score": 0.0, "details": {"images_found": 0}, "signals": signals}

    img_rate = img_found / n
    if img_rate >= 0.95:
        score += 30
    elif img_rate >= 0.8:
        score += 20
    elif img_rate >= 0.5:
        score += 12
    else:
        score += 5
    signals.append(f"image coverage: {img_found}/{n}")

    if https_imgs == img_found:
        score += 15
        signals.append("all images HTTPS")
    elif https_imgs > 0:
        score += 8
        signals.append(f"HTTPS images: {https_imgs}/{img_found}")

    if valid_format == img_found:
        score += 10
        signals.append("all valid image formats")
    elif valid_format > 0:
        score += 5

    additional_imgs = sum(1 for p in sample if p.get("additional_image_link") or p.get("additional_image"))
    if additional_imgs > 0:
        score += 15
        signals.append(f"additional images: {additional_imgs} products")

    modern_format = sum(1 for p in sample
                       if re.search(r'\.(webp|avif)', str(p.get("image_link", "")), re.IGNORECASE))
    if modern_format > 0:
        score += 10
        signals.append(f"modern formats (WebP/AVIF): {modern_format}")

    large_imgs = sum(1 for p in sample
                    if re.search(r'(large|1200|1024|800x|_L\.)', str(p.get("image_link", "")), re.IGNORECASE))
    if large_imgs > 0:
        score += 10
        signals.append(f"high-res indicators: {large_imgs}")

    alt_text = sum(1 for p in sample if p.get("image_alt") or p.get("image_title"))
    if alt_text > 0:
        score += 10
        signals.append(f"image alt/title: {alt_text}")

    score = round(min(100, score), 1)
    return {
        "score": score,
        "details": {
            "images_found": img_found,
            "https_images": https_imgs,
            "valid_format": valid_format,
            "additional_images": additional_imgs,
            "modern_format": modern_format,
        },
        "signals": signals,
    }


def score_platform_compliance(products: list, platform: str = "google") -> dict:
    """Score platform-specific compliance requirements (0-100)."""
    if not products:
        return {"score": 0.0, "details": {"platform": platform}, "issues": []}

    score = 0.0
    issues = []
    sample = products[:20]
    n = len(sample)

    if platform == "google":
        gtin_count = sum(1 for p in sample if p.get("gtin") or p.get("gtin13") or p.get("gtin14"))
        mpn_count = sum(1 for p in sample if p.get("mpn"))
        brand_count = sum(1 for p in sample if p.get("brand"))

        identifier_rate = (gtin_count + mpn_count) / n if n > 0 else 0
        if identifier_rate >= 0.8:
            score += 25
        elif identifier_rate >= 0.5:
            score += 15
        elif identifier_rate > 0:
            score += 8
        else:
            issues.append("no GTIN/MPN identifiers found (Google requires for most categories)")

        if brand_count / n >= 0.9:
            score += 15
        elif brand_count > 0:
            score += 8
        else:
            issues.append("missing brand field")

        category_count = sum(1 for p in sample if p.get("google_product_category") or p.get("product_type"))
        if category_count / n >= 0.8:
            score += 15
        elif category_count > 0:
            score += 8
        else:
            issues.append("missing product category/type")

        avail_count = sum(1 for p in sample if p.get("availability"))
        valid_avail = sum(1 for p in sample
                        if p.get("availability", "").lower() in ("in stock", "in_stock", "out of stock", "out_of_stock", "preorder", "backorder"))
        if valid_avail / n >= 0.9:
            score += 15
        elif avail_count > 0:
            score += 8
            if valid_avail < avail_count:
                issues.append(f"non-standard availability values ({avail_count - valid_avail} items)")
        else:
            issues.append("missing availability field")

        condition_count = sum(1 for p in sample if p.get("condition"))
        valid_condition = sum(1 for p in sample
                            if p.get("condition", "").lower() in ("new", "refurbished", "used"))
        if valid_condition / n >= 0.9:
            score += 10
        elif condition_count > 0:
            score += 5

        shipping_count = sum(1 for p in sample if p.get("shipping") or p.get("shipping_weight"))
        if shipping_count > 0:
            score += 10
        else:
            issues.append("no shipping info")

        color_size = sum(1 for p in sample if p.get("color") or p.get("size"))
        if color_size > 0:
            score += 5

        custom_labels = sum(1 for p in sample if any(p.get(f"custom_label_{i}") for i in range(5)))
        if custom_labels > 0:
            score += 5

    elif platform == "naver":
        cat1 = sum(1 for p in sample if p.get("category1"))
        cat2 = sum(1 for p in sample if p.get("category2"))
        cat3 = sum(1 for p in sample if p.get("category3"))

        if cat1 / n >= 0.9:
            score += 20
        elif cat1 > 0:
            score += 10
        else:
            issues.append("missing category1 (required for Naver)")

        if cat2 > 0:
            score += 10
        if cat3 > 0:
            score += 5

        shipping_count = sum(1 for p in sample if p.get("shipping"))
        if shipping_count / n >= 0.9:
            score += 15
        elif shipping_count > 0:
            score += 8
        else:
            issues.append("missing shipping info (required for Naver)")

        price_pc = sum(1 for p in sample if p.get("price_pc"))
        if price_pc / n >= 0.9:
            score += 15
        elif price_pc > 0:
            score += 8
        else:
            issues.append("missing price_pc (required for Naver)")

        manufacture = sum(1 for p in sample if p.get("manufacture") or p.get("brand"))
        if manufacture > 0:
            score += 10

        origin = sum(1 for p in sample if p.get("origin"))
        if origin > 0:
            score += 5

        import_flag = sum(1 for p in sample if p.get("import_flag"))
        if import_flag > 0:
            score += 5

        event = sum(1 for p in sample if p.get("event_words") or p.get("card_event"))
        if event > 0:
            score += 10

        model = sum(1 for p in sample if p.get("model_no"))
        if model > 0:
            score += 5

    score = round(max(0, min(100, score)), 1)
    return {"score": score, "details": {"platform": platform, "sample_size": n}, "issues": issues}


# ---------------------------------------------------------------------------
# Orchestrators
# ---------------------------------------------------------------------------

def validate_feed_content(content: str, platform: str = "google") -> dict:
    """Full 6-dimension feed validation on raw content."""
    parsed = parse_product_feed(content)
    products = parsed["products"]

    dq = score_data_quality(products)
    fc = score_field_completeness(products, platform)
    ff = score_feed_freshness(content)
    pa = score_pricing_accuracy(products)
    mq = score_media_quality(products)
    pc = score_platform_compliance(products, platform)

    dimensions = {
        "data_quality": dq["score"],
        "field_completeness": fc["score"],
        "feed_freshness": ff["score"],
        "pricing_accuracy": pa["score"],
        "media_quality": mq["score"],
        "platform_compliance": pc["score"],
    }

    overall = round(sum(dimensions[k] * DIMENSION_WEIGHTS[k] for k in DIMENSION_WEIGHTS), 1)

    issues = []
    if dq["score"] < 40:
        issues.append({"severity": "high", "message": f"데이터 품질 미흡 — {len(dq['issues'])}건의 문제"})
    if fc["details"].get("missing_required"):
        missing = fc["details"]["missing_required"]
        issues.append({"severity": "high", "message": f"필수 필드 누락: {', '.join(missing[:5])}"})
    if ff["score"] < 40:
        issues.append({"severity": "medium", "message": "피드 최신성 부족 — 날짜 신호 확인 필요"})
    if pa["score"] < 30:
        issues.append({"severity": "high", "message": "가격 정보 부정확 — 통화/형식 확인 필요"})
    if mq["score"] < 30 and mq["details"].get("images_found", 0) == 0:
        issues.append({"severity": "high", "message": "이미지 없음 — image_link 필드 추가 필요"})
    if pc["score"] < 40:
        issues.append({"severity": "medium", "message": f"{platform} 플랫폼 규정 미준수 항목 확인"})
    if parsed["total_items"] == 0:
        issues.append({"severity": "critical", "message": "피드에 상품이 없습니다"})

    for issue_text in dq["issues"][:3]:
        issues.append({"severity": "low", "message": issue_text})
    for issue_text in pa["issues"][:3]:
        issues.append({"severity": "low", "message": issue_text})
    for issue_text in pc["issues"][:3]:
        issues.append({"severity": "low", "message": issue_text})

    return {
        "score": overall,
        "platform": platform,
        "dimensions": dimensions,
        "details": {
            "data_quality": dq,
            "field_completeness": fc,
            "feed_freshness": ff,
            "pricing_accuracy": pa,
            "media_quality": mq,
            "platform_compliance": pc,
        },
        "statistics": {
            "total_products": parsed["total_items"],
            "sample_validated": parsed["parsed_sample"],
        },
        "field_coverage": fc.get("coverage", {}),
        "issues": issues,
    }


def detect_feed(url: str) -> dict:
    """Detect product feed from site URL."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    feed_paths = [
        "/feed.xml", "/products.xml", "/merchant-feed.xml",
        "/product-feed.xml", "/shopping-feed.xml",
        "/sitemap-products.xml", "/feed/products",
    ]

    for path in feed_paths:
        feed_url = base + path
        result = fetch_page(feed_url)
        if result["success"] and result.get("status_code") == 200:
            content = result.get("html", "")
            if "<item" in content or "<entry" in content or "<product" in content:
                return {"found": True, "url": feed_url, "content": content}

    return {"found": False}


def validate_feed(url: str, platform: str = "google") -> dict:
    """Full product feed validation (URL-based entry point)."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    if url.endswith(".xml") or "/feed" in url:
        result = fetch_page(url)
        if result["success"] and result.get("status_code") == 200:
            feed_data = {"found": True, "url": url, "content": result["html"]}
        else:
            feed_data = {"found": False}
    else:
        feed_data = detect_feed(url)

    if not feed_data["found"]:
        return {
            "success": True,
            "url": url,
            "feed_found": False,
            "score": 0,
            "issues": [{"severity": "critical", "message": "No product feed found"}],
        }

    analysis = validate_feed_content(feed_data["content"], platform)
    analysis["success"] = True
    analysis["url"] = url
    analysis["feed_found"] = True
    analysis["feed_url"] = feed_data["url"]
    return analysis


def main():
    parser = argparse.ArgumentParser(description="AAO product feed validation — 6-dimension scoring")
    parser.add_argument("url", help="Feed URL or site URL")
    parser.add_argument("--platform", choices=["google", "naver"], default="google", help="Target platform")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = validate_feed(args.url, args.platform)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("feed_found"):
            print(f"Feed Score: {result['score']}/100 ({args.platform})")
            print(f"Products: {result['statistics']['total_products']}")
            print("\nDimensions:")
            for dim, w in DIMENSION_WEIGHTS.items():
                s = result["dimensions"][dim]
                bar = "█" * int(s / 5) + "░" * (20 - int(s / 5))
                print(f"  {dim:25s} {bar} {s:5.1f} (×{w})")
            for issue in result.get("issues", []):
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print("No product feed found")
            for issue in result.get("issues", []):
                print(f"  [{issue['severity'].upper()}] {issue['message']}")


if __name__ == "__main__":
    main()
