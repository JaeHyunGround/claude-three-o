<!-- Updated: 2026-05-04 -->
# Industry Detection Rules (Korean Market)

## Detection Priority

Check signals in order. First match with 3+ signals wins.

## Industry Profiles

### Franchise HQ (프랜차이즈 본사)
**Signals:**
- Multiple branch/store location pages (/stores, /branches, /locations, /매장안내)
- Franchise application page (/franchise, /가맹문의)
- Branch-specific phone numbers or addresses (3+ locations)
- Franchise FAQ or partner program
- Uniform branding with location variants

**Module Priority:** GEO +5%, AAO +5%
**Reason:** Multi-brand tracking and multi-location agent scenarios critical

### Academy / Education (학원/교육)
**Signals:**
- Course or curriculum pages (/courses, /curriculum, /수강안내, /강좌)
- Class schedule or timetable (/schedule, /시간표)
- Instructor/teacher profiles
- Student reviews or success stories
- Registration/enrollment CTA

**Module Priority:** GEO +10%
**Reason:** Comparison queries dominant ("best academy for...", "A vs B academy")

### Clinic / Healthcare (병원/의료)
**Signals:**
- Doctor profiles with specializations (/doctors, /의료진)
- Department listings (/departments, /진료과)
- Appointment booking system
- Medical terminology in content
- Medical license or certification mentions

**Module Priority:** GEO +10%
**Reason:** Trust-sensitive queries; AI recommendations carry high responsibility

### Restaurant / F&B (음식점/요식업)
**Signals:**
- Menu page with prices (/menu, /메뉴)
- Reservation system (/reservation, /예약)
- Naver Place or Kakao Map embed
- Food photography galleries
- Operating hours prominently displayed

**Module Priority:** SEO +5%
**Reason:** Naver Place ranking is primary discovery channel

### E-commerce (이커머스)
**Signals:**
- Product listing pages (/products, /collections, /상품)
- Shopping cart functionality (/cart, /장바구니)
- Product schema markup (Product, Offer)
- Naver Smart Store link or integration
- Price and availability display
- "Add to cart" or "Buy now" CTAs

**Module Priority:** AAO +10%
**Reason:** Product feed completeness directly impacts AI agent purchasing flow

### Real Estate (부동산)
**Signals:**
- Property listings with filters (/listings, /매물)
- Property search with map (/map, /지도검색)
- Area/neighborhood guides
- Agent profiles
- Price range or square meter data

**Module Priority:** SEO +5%, AAO +5%
**Reason:** Local search + structured property data for AI agents

### SaaS (소프트웨어)
**Signals:**
- Pricing page with tiers (/pricing, /요금제)
- Feature comparison page (/features)
- Documentation or API docs (/docs, /api)
- Free trial or sign-up CTA
- Integration pages (/integrations)

**Module Priority:** GEO +5%, AAO +5%
**Reason:** AI comparison queries + API-based data integration

### Agency (에이전시/대행사)
**Signals:**
- Portfolio or case studies (/portfolio, /case-studies, /포트폴리오)
- Client logos or testimonials
- Service pages by industry (/industries, /서비스)
- Team or about page with expertise areas
- "Our work" or "Results" sections

**Module Priority:** Default weights
**Reason:** Balanced across all pillars

## Language Detection

| Signal | Classification |
|--------|---------------|
| `<html lang="ko">` | Korean primary |
| Naver analytics script | Korean market |
| `.co.kr` or `.kr` domain | Korean market |
| Korean characters > 50% of body text | Korean content |
| Naver Search Advisor meta tag | Korean SEO active |

When Korean market detected, auto-suggest Naver-specific analysis.
