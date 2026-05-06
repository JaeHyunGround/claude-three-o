<!-- Updated: 2026-05-04 -->
# Conversion Patterns by Industry

## Restaurant / F&B

### Ideal Flow:
```
Menu page (structured) → Reservation widget → Date/time/party → Confirm
```

### Required signals:
- Menu with prices (Schema: Menu, MenuItem)
- Reservation system (embedded or API)
- Available times visible without login
- Confirmation with reservation ID

### Korean market specifics:
- Naver Booking integration (네이버 예약)
- Kakao Channel booking
- Catchtable / TableManager integration

## Clinic / Healthcare

### Ideal Flow:
```
Service page → Doctor selection → Available slots → Patient info → Confirm
```

### Required signals:
- Service list with Schema (MedicalProcedure)
- Doctor profiles (Schema: Physician)
- Online booking system
- Insurance info available

### Korean market specifics:
- 똑닥 (DDokDak) integration
- Naver Hospital booking
- 진료과목 structured data

## Academy / Education

### Ideal Flow:
```
Course catalog → Course detail → Enrollment form → Payment → Confirmation
```

### Required signals:
- Course list (Schema: Course, CourseInstance)
- Pricing visible
- Schedule/calendar
- Level/prerequisite info
- Trial lesson option

### Korean market specifics:
- Level test reservation
- 수강료 안내 (tuition info page)
- Trial class booking

## E-commerce

### Ideal Flow:
```
Product page → Add to cart → Checkout → Payment → Order confirmation
```

### Required signals:
- Product schema (Schema: Product, Offer)
- Price, availability, shipping info
- Guest checkout option
- Multiple payment methods
- Order tracking

### Korean market specifics:
- Naver Pay integration
- Kakao Pay support
- 무통장입금 option visibility
- Shipping: 택배사 tracking API

## SaaS

### Ideal Flow:
```
Pricing page → Plan selection → Signup form → Payment → Dashboard
```

### Required signals:
- Pricing tiers clearly structured
- Free trial without credit card
- API documentation link
- Integration list
- Self-service signup

## Franchise (Multi-location)

### Ideal Flow:
```
Location finder → Nearest store → Store detail → Action (visit/order/book)
```

### Required signals:
- Store locator with structured data per location
- Each location has own action capability
- Consistent info across locations
- Delivery/pickup options clear
