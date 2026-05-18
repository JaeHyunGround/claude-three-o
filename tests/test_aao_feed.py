"""Tests for AAO product feed validation — 6-dimension quality scoring.

Covers: parse_product_feed, score_data_quality, score_field_completeness,
score_feed_freshness, score_pricing_accuracy, score_media_quality,
score_platform_compliance, validate_feed_content.
"""

import sys
import os
from datetime import datetime


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from aao_feed import (
    CURRENT_YEAR,
    DIMENSION_WEIGHTS,
    GOOGLE_REQUIRED,
    NAVER_REQUIRED,
    parse_product_feed,
    score_data_quality,
    score_field_completeness,
    score_feed_freshness,
    score_pricing_accuracy,
    score_media_quality,
    score_platform_compliance,
    validate_feed_content,
)


# ---------------------------------------------------------------------------
# Helpers — product & feed builders
# ---------------------------------------------------------------------------

def _product(**overrides):
    """Build a single product dict with sensible defaults."""
    base = {
        "id": f"SKU-{id(overrides) % 100000:05d}",
        "title": "프리미엄 무선 블루투스 이어폰 노이즈 캔슬링",
        "description": "최신 블루투스 5.3 기술을 적용한 프리미엄 노이즈 캔슬링 무선 이어폰입니다. 최대 30시간 재생 가능.",
        "link": "https://example.com/product/earphone-001",
        "image_link": "https://cdn.example.com/images/earphone-001.webp",
        "price": "89000 KRW",
        "availability": "in stock",
        "condition": "new",
        "brand": "SkyAudio",
    }
    base.update(overrides)
    return base


def _products(n, **common_overrides):
    """Build n unique products."""
    items = []
    for i in range(n):
        p = _product(
            id=f"SKU-{i:05d}",
            title=f"상품 {i} — 고품질 블루투스 이어폰 프리미엄 에디션",
            link=f"https://example.com/product/{i}",
            image_link=f"https://cdn.example.com/img/{i}.webp",
        )
        p.update(common_overrides)
        items.append(p)
    return items


def _naver_product(**overrides):
    """Build a Naver-compliant product."""
    base = {
        "id": f"NV-{id(overrides) % 100000:05d}",
        "title": "네이버 쇼핑 전용 블루투스 스피커 30W",
        "price_pc": "45000",
        "link": "https://smartstore.naver.com/shop/products/123",
        "image_link": "https://shop-phinf.pstatic.net/img/speaker.jpg",
        "category1": "디지털/가전",
        "shipping": "0",
    }
    base.update(overrides)
    return base


def _naver_products(n, **common_overrides):
    items = []
    for i in range(n):
        p = _naver_product(
            id=f"NV-{i:05d}",
            title=f"네이버 상품 {i} — 고급 블루투스 스피커 휴대용",
            link=f"https://smartstore.naver.com/shop/products/{i}",
            image_link=f"https://shop-phinf.pstatic.net/img/{i}.jpg",
        )
        p.update(common_overrides)
        items.append(p)
    return items


def _wrap_feed(products_xml: str) -> str:
    """Wrap product XML fragments in a channel/rss envelope."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
<channel>
<title>Test Feed</title>
<lastBuildDate>{CURRENT_YEAR}-01-15T10:00:00Z</lastBuildDate>
{products_xml}
</channel>
</rss>"""


def _product_xml(product: dict) -> str:
    """Convert a product dict to <item> XML."""
    fields = "\n".join(f"<g:{k}>{v}</g:{k}>" for k, v in product.items())
    return f"<item>\n{fields}\n</item>"


def _build_feed(products: list) -> str:
    """Build a complete XML feed from product dicts."""
    items = "\n".join(_product_xml(p) for p in products)
    return _wrap_feed(items)


# ===================================================================
# parse_product_feed
# ===================================================================

class TestParseProductFeed:
    def test_empty_content(self):
        r = parse_product_feed("")
        assert r["total_items"] == 0
        assert r["products"] == []

    def test_single_item(self):
        xml = _build_feed([_product()])
        r = parse_product_feed(xml)
        assert r["total_items"] == 1
        assert len(r["products"]) == 1
        assert r["products"][0]["title"]

    def test_multiple_items(self):
        xml = _build_feed(_products(5))
        r = parse_product_feed(xml)
        assert r["total_items"] == 5
        assert r["parsed_sample"] == 5

    def test_entry_tag(self):
        content = "<feed><entry><title>Atom Product</title><id>A1</id></entry></feed>"
        r = parse_product_feed(content)
        assert r["total_items"] == 1
        assert r["products"][0].get("title") == "Atom Product"

    def test_product_tag(self):
        content = "<products><product><title>Custom</title><id>C1</id></product></products>"
        r = parse_product_feed(content)
        assert r["total_items"] == 1

    def test_sample_cap_20(self):
        xml = _build_feed(_products(30))
        r = parse_product_feed(xml)
        assert r["total_items"] == 30
        assert len(r["products"]) <= 20

    def test_simple_fields_fallback(self):
        content = "<feed><item><title>Simple</title><price>1000</price></item></feed>"
        r = parse_product_feed(content)
        assert r["total_items"] == 1
        assert r["products"][0]["title"] == "Simple"


# ===================================================================
# score_data_quality
# ===================================================================

class TestScoreDataQuality:
    def test_empty(self):
        r = score_data_quality([])
        assert r["score"] == 0.0
        assert r["details"]["checked"] == 0

    def test_perfect_products(self):
        products = _products(5)
        r = score_data_quality(products)
        assert r["score"] >= 70
        assert r["details"]["valid_titles"] == 5
        assert r["details"]["valid_descs"] == 5
        assert r["details"]["valid_links"] == 5

    def test_missing_titles(self):
        products = _products(5, title="")
        r = score_data_quality(products)
        assert any("missing titles" in i for i in r["issues"])

    def test_short_titles(self):
        products = _products(5, title="짧음")
        r = score_data_quality(products)
        assert any("short titles" in i for i in r["issues"])

    def test_duplicate_titles_penalty(self):
        products = [_product(id=f"SKU-{i}", title="동일 상품명 블루투스 이어폰") for i in range(5)]
        r = score_data_quality(products)
        assert any("uniqueness" in i for i in r["issues"])

    def test_missing_descriptions(self):
        products = _products(5, description="")
        r = score_data_quality(products)
        assert any("missing descriptions" in i for i in r["issues"])
        assert r["details"]["valid_descs"] == 0

    def test_short_descriptions_count_invalid(self):
        products = _products(5, description="짧은 설명")
        r = score_data_quality(products)
        assert r["details"]["valid_descs"] == 0

    def test_invalid_links(self):
        products = _products(5, link="not-a-url")
        r = score_data_quality(products)
        assert any("invalid" in i.lower() or "missing" in i.lower() for i in r["issues"])

    def test_https_bonus(self):
        http_products = _products(5, link="http://example.com/p")
        https_products = _products(5, link="https://example.com/p")
        r_http = score_data_quality(http_products)
        r_https = score_data_quality(https_products)
        assert r_https["score"] >= r_http["score"]

    def test_duplicate_ids(self):
        products = [_product(id="SAME-ID", title=f"Product {i} premium bluetooth") for i in range(5)]
        r = score_data_quality(products)
        assert any("duplicate" in i.lower() for i in r["issues"])

    def test_html_in_fields_penalty(self):
        products = _products(3, description="<b>Bold</b> description with <a href='#'>link</a> inside the field")
        r = score_data_quality(products)
        assert any("HTML" in i for i in r["issues"])

    def test_many_empty_fields_penalty(self):
        products = [{"id": f"SKU-{i}", "title": f"Prod {i} premium item", "a": "", "b": "", "c": "", "d": ""} for i in range(5)]
        r = score_data_quality(products)
        assert any("empty field" in i for i in r["issues"])

    def test_rich_products_field_count_bonus(self):
        products = _products(3)
        for p in products:
            p.update({"gtin": "123456789", "color": "black", "size": "M", "material": "cotton"})
        r = score_data_quality(products)
        assert r["score"] >= 70

    def test_score_clamped_0_100(self):
        products = _products(5)
        r = score_data_quality(products)
        assert 0 <= r["score"] <= 100

    def test_single_product(self):
        r = score_data_quality([_product()])
        assert r["score"] > 0
        assert r["details"]["checked"] == 1


# ===================================================================
# score_field_completeness
# ===================================================================

class TestScoreFieldCompleteness:
    def test_empty_products(self):
        r = score_field_completeness([], "google")
        assert r["score"] == 0.0
        assert r["details"]["missing_required"] == GOOGLE_REQUIRED

    def test_google_full_required(self):
        products = _products(5)
        r = score_field_completeness(products, "google")
        assert r["score"] >= 60
        assert r["details"]["required_avg"] >= 80

    def test_google_missing_required(self):
        products = _products(5, brand="", condition="")
        r = score_field_completeness(products, "google")
        assert "brand" in r["details"]["missing_required"]
        assert "condition" in r["details"]["missing_required"]

    def test_google_with_recommended(self):
        products = _products(3)
        for p in products:
            p.update({"gtin": "1234567890123", "google_product_category": "Electronics", "sale_price": "79000 KRW"})
        r = score_field_completeness(products, "google")
        assert r["details"]["optional_avg"] > 0
        assert r["score"] > score_field_completeness(_products(3), "google")["score"]

    def test_naver_full_required(self):
        products = _naver_products(5)
        r = score_field_completeness(products, "naver")
        assert r["score"] >= 50
        assert r["details"]["platform"] == "naver"

    def test_naver_missing_required(self):
        products = _naver_products(5, category1="", shipping="")
        r = score_field_completeness(products, "naver")
        assert "category1" in r["details"]["missing_required"]

    def test_coverage_dict(self):
        products = _products(5)
        r = score_field_completeness(products, "google")
        assert isinstance(r["coverage"], dict)
        assert "title" in r["coverage"]

    def test_score_formula_75_25(self):
        products = _products(5)
        r = score_field_completeness(products, "google")
        expected = r["details"]["required_avg"] * 0.75 + r["details"]["optional_avg"] * 0.25
        assert abs(r["score"] - round(min(100, expected), 1)) < 0.2

    def test_sample_cap(self):
        products = _products(30)
        r = score_field_completeness(products, "google")
        assert r["score"] > 0


# ===================================================================
# score_feed_freshness
# ===================================================================

class TestScoreFeedFreshness:
    def test_empty(self):
        r = score_feed_freshness("")
        assert r["score"] == 0.0
        assert r["signals"] == []

    def test_current_year_dates(self):
        content = f"<item><updated>{CURRENT_YEAR}-06-15</updated></item>"
        r = score_feed_freshness(content)
        assert r["score"] >= 30
        assert any("current year" in s for s in r["signals"])

    def test_last_year_dates(self):
        content = f"<item><date>{CURRENT_YEAR - 1}-11-20</date></item>"
        r = score_feed_freshness(content)
        assert r["score"] >= 15
        assert any("last year" in s for s in r["signals"])

    def test_old_dates(self):
        content = f"<item><date>{CURRENT_YEAR - 2}-01-01</date></item>"
        r = score_feed_freshness(content)
        assert r["score"] >= 5
        assert any("aging" in s for s in r["signals"])

    def test_lastbuilddate(self):
        content = f"<lastBuildDate>{CURRENT_YEAR}-03-01T10:00:00Z</lastBuildDate>"
        r = score_feed_freshness(content)
        assert any("lastBuildDate" in s for s in r["signals"])

    def test_pubdate(self):
        content = "<pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>"
        r = score_feed_freshness(content)
        assert any("pubDate" in s for s in r["signals"])

    def test_updated_tag(self):
        content = "<updated>2024-01-01T00:00:00Z</updated>"
        r = score_feed_freshness(content)
        assert any("updated" in s for s in r["signals"])

    def test_modified_tag(self):
        content = "<modified>2024-01-01</modified>"
        r = score_feed_freshness(content)
        assert any("modified" in s for s in r["signals"])

    def test_fast_ttl(self):
        content = "<ttl>30</ttl>"
        r = score_feed_freshness(content)
        assert any("fast refresh" in s for s in r["signals"])
        assert r["score"] >= 15

    def test_daily_ttl(self):
        content = "<ttl>720</ttl>"
        r = score_feed_freshness(content)
        assert any("daily refresh" in s for s in r["signals"])

    def test_slow_ttl(self):
        content = "<ttl>10080</ttl>"
        r = score_feed_freshness(content)
        assert any("slow refresh" in s for s in r["signals"])

    def test_availability_signal(self):
        content = "<g:availability>in stock</g:availability><g:availability>out of stock</g:availability>"
        r = score_feed_freshness(content)
        assert any("availability" in s for s in r["signals"])

    def test_sale_price_signal(self):
        content = "<g:sale_price>50000 KRW</g:sale_price>"
        r = score_feed_freshness(content)
        assert any("sale" in s for s in r["signals"])

    def test_max_score_cap(self):
        content = f"""
        <lastBuildDate>{CURRENT_YEAR}-06-01</lastBuildDate>
        <pubDate>{CURRENT_YEAR}-06-01</pubDate>
        <updated>{CURRENT_YEAR}-06-01</updated>
        <modified>{CURRENT_YEAR}-06-01</modified>
        <ttl>15</ttl>
        <g:availability>in stock</g:availability>
        <g:sale_price>5000</g:sale_price>
        <item><date>{CURRENT_YEAR}-06-15</date></item>
        """
        r = score_feed_freshness(content)
        assert r["score"] <= 100

    def test_combined_signals(self):
        content = f"""
        <lastBuildDate>{CURRENT_YEAR}-01-10</lastBuildDate>
        <ttl>60</ttl>
        <item><date>{CURRENT_YEAR}-01-10</date></item>
        """
        r = score_feed_freshness(content)
        assert r["score"] >= 50


# ===================================================================
# score_pricing_accuracy
# ===================================================================

class TestScorePricingAccuracy:
    def test_empty(self):
        r = score_pricing_accuracy([])
        assert r["score"] == 0.0

    def test_no_prices(self):
        products = [{"id": "1", "title": "No price product title"}]
        r = score_pricing_accuracy(products)
        assert r["score"] == 0.0
        assert any("no pricing" in i for i in r["issues"])

    def test_valid_prices_with_currency(self):
        products = _products(5)
        r = score_pricing_accuracy(products)
        assert r["score"] >= 50
        assert r["details"]["prices_found"] == 5
        assert r["details"]["has_currency"] == 5

    def test_prices_without_currency(self):
        products = _products(5, price="89000")
        r = score_pricing_accuracy(products)
        assert r["details"]["has_currency"] == 0
        assert r["score"] < score_pricing_accuracy(_products(5))["score"]

    def test_sale_price_valid(self):
        products = _products(3, price="100000 KRW", sale_price="79000 KRW")
        r = score_pricing_accuracy(products)
        assert r["details"]["sale_valid"] == 3
        assert r["score"] >= 60

    def test_sale_price_higher_than_regular(self):
        products = _products(3, price="50000 KRW", sale_price="80000 KRW")
        r = score_pricing_accuracy(products)
        assert any("sale price" in i.lower() for i in r["issues"])

    def test_zero_price_penalty(self):
        products = _products(3, price="0 KRW")
        r = score_pricing_accuracy(products)
        assert any("zero price" in i for i in r["issues"])

    def test_sale_effective_date_bonus(self):
        products = _products(3, sale_price_effective_date="2024-01-01/2024-01-31")
        r = score_pricing_accuracy(products)
        with_date = r["score"]
        r_no = score_pricing_accuracy(_products(3))
        assert with_date >= r_no["score"]

    def test_shipping_bonus(self):
        products = _products(3, shipping="KR:::0 KRW")
        r = score_pricing_accuracy(products)
        with_shipping = r["score"]
        r_no = score_pricing_accuracy(_products(3))
        assert with_shipping >= r_no["score"]

    def test_naver_price_pc(self):
        products = _naver_products(5)
        r = score_pricing_accuracy(products)
        assert r["details"]["prices_found"] > 0

    def test_mixed_valid_invalid_sale_prices(self):
        p1 = _product(id="1", price="100000 KRW", sale_price="80000 KRW")
        p2 = _product(id="2", price="50000 KRW", sale_price="70000 KRW")
        r = score_pricing_accuracy([p1, p2])
        assert r["details"]["sale_valid"] == 1
        assert any("invalid" in i.lower() or "sale price" in i.lower() for i in r["issues"])

    def test_score_clamped(self):
        products = _products(5)
        r = score_pricing_accuracy(products)
        assert 0 <= r["score"] <= 100


# ===================================================================
# score_media_quality
# ===================================================================

class TestScoreMediaQuality:
    def test_empty(self):
        r = score_media_quality([])
        assert r["score"] == 0.0

    def test_no_images(self):
        products = [{"id": "1", "title": "No Image Product Title"}]
        r = score_media_quality(products)
        assert r["score"] == 0.0
        assert any("no images" in s for s in r["signals"])

    def test_full_coverage_https_webp(self):
        products = _products(5)
        r = score_media_quality(products)
        assert r["score"] >= 50
        assert r["details"]["images_found"] == 5
        assert r["details"]["https_images"] == 5

    def test_http_images(self):
        products = _products(5, image_link="http://cdn.example.com/img.jpg")
        r = score_media_quality(products)
        assert r["details"]["https_images"] == 0
        r_https = score_media_quality(_products(5))
        assert r["score"] < r_https["score"]

    def test_additional_images_bonus(self):
        products = _products(3, additional_image_link="https://cdn.example.com/extra.jpg")
        r = score_media_quality(products)
        assert any("additional" in s for s in r["signals"])
        assert r["details"]["additional_images"] == 3

    def test_modern_format_bonus(self):
        products = _products(3, image_link="https://cdn.example.com/img.webp")
        r = score_media_quality(products)
        assert r["details"]["modern_format"] > 0

    def test_avif_format(self):
        products = _products(3, image_link="https://cdn.example.com/img.avif")
        r = score_media_quality(products)
        assert r["details"]["modern_format"] > 0

    def test_high_res_indicator(self):
        products = _products(3, image_link="https://cdn.example.com/product_1200x1200_L.jpg")
        r = score_media_quality(products)
        assert any("high-res" in s for s in r["signals"])

    def test_alt_text_bonus(self):
        products = _products(3, image_alt="프리미엄 블루투스 이어폰 이미지")
        r = score_media_quality(products)
        assert any("alt" in s for s in r["signals"])

    def test_partial_coverage(self):
        p1 = _product(id="1", image_link="https://cdn.example.com/a.jpg")
        p2 = _product(id="2", image_link="")
        r = score_media_quality([p1, p2])
        assert r["details"]["images_found"] == 1
        assert r["score"] > 0

    def test_no_valid_format(self):
        products = _products(3, image_link="https://cdn.example.com/img")
        r = score_media_quality(products)
        assert r["details"]["valid_format"] == 0

    def test_score_clamped(self):
        products = _products(5, additional_image_link="https://a.com/b.webp", image_alt="alt", image_title="title")
        r = score_media_quality(products)
        assert r["score"] <= 100


# ===================================================================
# score_platform_compliance — Google
# ===================================================================

class TestPlatformComplianceGoogle:
    def test_empty(self):
        r = score_platform_compliance([], "google")
        assert r["score"] == 0.0

    def test_full_compliance(self):
        products = _products(5)
        for p in products:
            p.update({
                "gtin": "1234567890123",
                "google_product_category": "Electronics > Audio",
                "shipping": "KR:::0 KRW",
                "color": "Black",
                "size": "One Size",
                "custom_label_0": "bestseller",
            })
        r = score_platform_compliance(products, "google")
        assert r["score"] >= 80

    def test_no_identifiers(self):
        products = _products(5)
        r = score_platform_compliance(products, "google")
        assert any("GTIN/MPN" in i for i in r["issues"])

    def test_gtin_present(self):
        products = _products(5, gtin="1234567890123")
        r = score_platform_compliance(products, "google")
        no_gtin = score_platform_compliance(_products(5), "google")
        assert r["score"] > no_gtin["score"]

    def test_mpn_present(self):
        products = _products(5, mpn="MPN-001")
        r = score_platform_compliance(products, "google")
        assert r["score"] > score_platform_compliance(_products(5), "google")["score"]

    def test_missing_brand(self):
        products = _products(5, brand="")
        r = score_platform_compliance(products, "google")
        assert any("brand" in i for i in r["issues"])

    def test_missing_category(self):
        products = [{"id": f"SKU-{i}", "title": f"Product {i}", "brand": "Brand"} for i in range(5)]
        r = score_platform_compliance(products, "google")
        assert any("category" in i for i in r["issues"])

    def test_valid_availability(self):
        products = _products(5, availability="in stock")
        r = score_platform_compliance(products, "google")
        assert r["score"] > 0

    def test_invalid_availability(self):
        products = _products(5, availability="available")
        r = score_platform_compliance(products, "google")
        assert any("availability" in i.lower() or "non-standard" in i.lower() for i in r["issues"])

    def test_missing_availability(self):
        products = _products(5, availability="")
        r = score_platform_compliance(products, "google")
        assert any("availability" in i for i in r["issues"])

    def test_condition_valid(self):
        products = _products(5, condition="new")
        r = score_platform_compliance(products, "google")
        assert r["score"] > 0

    def test_shipping_info(self):
        products = _products(5, shipping="KR:::3000 KRW")
        r = score_platform_compliance(products, "google")
        no_shipping = score_platform_compliance(_products(5, shipping=""), "google")
        assert r["score"] > no_shipping["score"]

    def test_color_size(self):
        products = _products(5, color="Red", size="L")
        r = score_platform_compliance(products, "google")
        assert r["score"] > score_platform_compliance(_products(5), "google")["score"]

    def test_custom_labels(self):
        products = _products(5, custom_label_0="summer-sale")
        r = score_platform_compliance(products, "google")
        assert r["score"] > score_platform_compliance(_products(5), "google")["score"]


# ===================================================================
# score_platform_compliance — Naver
# ===================================================================

class TestPlatformComplianceNaver:
    def test_empty(self):
        r = score_platform_compliance([], "naver")
        assert r["score"] == 0.0

    def test_full_compliance(self):
        products = _naver_products(5)
        for p in products:
            p.update({
                "category2": "음향기기",
                "category3": "블루투스 스피커",
                "manufacture": "SkyAudio",
                "origin": "한국",
                "import_flag": "N",
                "event_words": "여름 세일",
                "model_no": "SA-BT30",
            })
        r = score_platform_compliance(products, "naver")
        assert r["score"] >= 80

    def test_missing_category1(self):
        products = _naver_products(5, category1="")
        r = score_platform_compliance(products, "naver")
        assert any("category1" in i for i in r["issues"])

    def test_category_depth(self):
        products = _naver_products(5, category2="음향기기", category3="블루투스 스피커")
        r = score_platform_compliance(products, "naver")
        assert r["score"] > score_platform_compliance(_naver_products(5), "naver")["score"]

    def test_missing_shipping(self):
        products = _naver_products(5, shipping="")
        r = score_platform_compliance(products, "naver")
        assert any("shipping" in i for i in r["issues"])

    def test_missing_price_pc(self):
        products = _naver_products(5, price_pc="")
        r = score_platform_compliance(products, "naver")
        assert any("price_pc" in i for i in r["issues"])

    def test_manufacture_brand(self):
        products = _naver_products(5, manufacture="SkyAudio")
        r = score_platform_compliance(products, "naver")
        assert r["score"] > score_platform_compliance(_naver_products(5, manufacture="", brand=""), "naver")["score"]

    def test_origin(self):
        products = _naver_products(5, origin="한국")
        r = score_platform_compliance(products, "naver")
        assert r["score"] > score_platform_compliance(_naver_products(5), "naver")["score"]

    def test_import_flag(self):
        products = _naver_products(5, import_flag="N")
        r = score_platform_compliance(products, "naver")
        assert r["score"] > score_platform_compliance(_naver_products(5), "naver")["score"]

    def test_event_words(self):
        products = _naver_products(5, event_words="무료배송 이벤트")
        r = score_platform_compliance(products, "naver")
        assert r["score"] > score_platform_compliance(_naver_products(5), "naver")["score"]

    def test_model_no(self):
        products = _naver_products(5, model_no="SA-BT30")
        r = score_platform_compliance(products, "naver")
        assert r["score"] > score_platform_compliance(_naver_products(5), "naver")["score"]


# ===================================================================
# validate_feed_content — orchestrator
# ===================================================================

class TestValidateFeedContent:
    def test_empty_feed(self):
        r = validate_feed_content("")
        assert r["score"] == 0.0
        assert r["statistics"]["total_products"] == 0
        assert any(i["severity"] == "critical" for i in r["issues"])

    def test_full_google_feed(self):
        products = _products(10)
        for p in products:
            p.update({
                "gtin": "1234567890123",
                "google_product_category": "Electronics > Audio",
                "shipping": "KR:::0 KRW",
                "sale_price": "79000 KRW",
                "sale_price_effective_date": f"{CURRENT_YEAR}-01-01/{CURRENT_YEAR}-12-31",
                "additional_image_link": "https://cdn.example.com/extra.webp",
            })
        xml = _build_feed(products)
        r = validate_feed_content(xml, "google")
        assert r["score"] >= 50
        assert r["platform"] == "google"
        assert all(k in r["dimensions"] for k in DIMENSION_WEIGHTS)

    def test_full_naver_feed(self):
        products = _naver_products(10)
        for p in products:
            p.update({
                "category2": "음향기기",
                "category3": "블루투스 스피커",
                "manufacture": "SkyAudio",
                "origin": "한국",
            })
        items = "\n".join(f"<item>{''.join(f'<{k}>{v}</{k}>' for k, v in p.items())}</item>" for p in products)
        xml = _wrap_feed(items)
        r = validate_feed_content(xml, "naver")
        assert r["score"] >= 30
        assert r["platform"] == "naver"

    def test_dimension_weights_sum(self):
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_overall_is_weighted_sum(self):
        products = _products(5)
        xml = _build_feed(products)
        r = validate_feed_content(xml, "google")
        recalc = sum(r["dimensions"][k] * DIMENSION_WEIGHTS[k] for k in DIMENSION_WEIGHTS)
        assert abs(r["score"] - round(recalc, 1)) < 0.2

    def test_issues_severity_levels(self):
        r = validate_feed_content("")
        severities = {i["severity"] for i in r["issues"]}
        assert "critical" in severities

    def test_low_data_quality_issue(self):
        products = _products(5, title="", description="", link="bad")
        xml = _build_feed(products)
        r = validate_feed_content(xml, "google")
        assert any("데이터 품질" in i["message"] for i in r["issues"])

    def test_missing_required_fields_issue(self):
        products = [{"id": str(i), "title": f"Product {i} minimal"} for i in range(5)]
        items = "\n".join(f"<item><id>{p['id']}</id><title>{p['title']}</title></item>" for p in products)
        xml = _wrap_feed(items)
        r = validate_feed_content(xml, "google")
        assert any("필수 필드" in i["message"] for i in r["issues"])

    def test_low_freshness_issue(self):
        products = _products(3)
        items = "\n".join(_product_xml(p) for p in products)
        xml = f"<rss><channel>{items}</channel></rss>"
        r = validate_feed_content(xml, "google")
        has_freshness_issue = any("최신성" in i["message"] for i in r["issues"])
        ff_score = r["dimensions"]["feed_freshness"]
        if ff_score < 40:
            assert has_freshness_issue

    def test_field_coverage_in_result(self):
        products = _products(5)
        xml = _build_feed(products)
        r = validate_feed_content(xml, "google")
        assert isinstance(r["field_coverage"], dict)

    def test_statistics(self):
        products = _products(8)
        xml = _build_feed(products)
        r = validate_feed_content(xml, "google")
        assert r["statistics"]["total_products"] == 8

    def test_details_structure(self):
        products = _products(3)
        xml = _build_feed(products)
        r = validate_feed_content(xml, "google")
        assert "data_quality" in r["details"]
        assert "field_completeness" in r["details"]
        assert "feed_freshness" in r["details"]
        assert "pricing_accuracy" in r["details"]
        assert "media_quality" in r["details"]
        assert "platform_compliance" in r["details"]


# ===================================================================
# Edge cases & integration
# ===================================================================

class TestEdgeCases:
    def test_single_product_feed(self):
        xml = _build_feed([_product()])
        r = validate_feed_content(xml, "google")
        assert r["score"] > 0

    def test_products_over_20_sample(self):
        xml = _build_feed(_products(50))
        r = validate_feed_content(xml, "google")
        assert r["statistics"]["total_products"] == 50
        assert r["details"]["data_quality"]["details"]["checked"] <= 20

    def test_unicode_content(self):
        p = _product(title="한글 상품명 프리미엄 블루투스 이어폰", description="이것은 한국어 설명입니다. 고품질의 프리미엄 블루투스 이어폰을 지금 만나보세요.")
        xml = _build_feed([p])
        r = validate_feed_content(xml, "google")
        assert r["score"] > 0

    def test_mixed_platforms_detect(self):
        products = _products(5)
        xml = _build_feed(products)
        r_google = validate_feed_content(xml, "google")
        r_naver = validate_feed_content(xml, "naver")
        assert r_google["platform"] == "google"
        assert r_naver["platform"] == "naver"

    def test_no_pricing_low_score(self):
        products = [{"id": str(i), "title": f"Product {i} without price data"} for i in range(5)]
        items = "\n".join(f"<item><id>{p['id']}</id><title>{p['title']}</title></item>" for p in products)
        xml = _wrap_feed(items)
        r = validate_feed_content(xml, "google")
        assert r["dimensions"]["pricing_accuracy"] == 0.0

    def test_no_images_low_score(self):
        products = [{"id": str(i), "title": f"Product {i} without image"} for i in range(5)]
        items = "\n".join(f"<item><id>{p['id']}</id><title>{p['title']}</title></item>" for p in products)
        xml = _wrap_feed(items)
        r = validate_feed_content(xml, "google")
        assert r["dimensions"]["media_quality"] == 0.0

    def test_current_year_dynamic(self):
        assert CURRENT_YEAR == datetime.now().year

    def test_dimension_weights_keys(self):
        expected = {"data_quality", "field_completeness", "feed_freshness", "pricing_accuracy", "media_quality", "platform_compliance"}
        assert set(DIMENSION_WEIGHTS.keys()) == expected

    def test_google_required_fields_list(self):
        assert "id" in GOOGLE_REQUIRED
        assert "title" in GOOGLE_REQUIRED
        assert "price" in GOOGLE_REQUIRED
        assert "brand" in GOOGLE_REQUIRED

    def test_naver_required_fields_list(self):
        assert "id" in NAVER_REQUIRED
        assert "title" in NAVER_REQUIRED
        assert "price_pc" in NAVER_REQUIRED
        assert "category1" in NAVER_REQUIRED

    def test_score_zero_for_garbage(self):
        r = validate_feed_content("this is not xml at all just random garbage text", "google")
        assert r["score"] == 0.0

    def test_atom_feed_format(self):
        content = f"""
        <feed xmlns="http://www.w3.org/2005/Atom">
        <updated>{CURRENT_YEAR}-01-01</updated>
        <entry><title>Atom Product One Title</title><id>A1</id></entry>
        <entry><title>Atom Product Two Title</title><id>A2</id></entry>
        </feed>"""
        r = validate_feed_content(content, "google")
        assert r["statistics"]["total_products"] == 2
