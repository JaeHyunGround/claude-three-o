<!-- Updated: 2026-05-04 -->
# Schema.org Requirements for Agent Consumption

## Organization (Homepage)

```json
{
  "@type": "Organization",
  "name": "Required",
  "url": "Required",
  "logo": "Required",
  "description": "Recommended",
  "sameAs": ["Required - all official profiles"],
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "Required",
    "contactType": "Required",
    "availableLanguage": "Recommended"
  },
  "address": "Required for local",
  "foundingDate": "Recommended",
  "numberOfEmployees": "Recommended"
}
```

## LocalBusiness (Location Pages)

```json
{
  "@type": "[Specific subtype]",
  "name": "Required",
  "address": "Required (full PostalAddress)",
  "geo": "Required (lat/lng)",
  "telephone": "Required",
  "openingHoursSpecification": "Required",
  "priceRange": "Recommended",
  "servesCuisine": "If restaurant",
  "menu": "If restaurant",
  "acceptsReservations": "If applicable",
  "aggregateRating": "Highly recommended",
  "review": "Recommended (recent)"
}
```

### Korean LocalBusiness Subtypes:
- Restaurant → `Restaurant` or `FoodEstablishment`
- Clinic → `MedicalBusiness` or specific (Dentist, etc.)
- Academy → `EducationalOrganization`
- Cafe → `CafeOrCoffeeShop`
- Gym → `ExerciseGym` or `SportsActivityLocation`
- Salon → `BeautySalon` or `HairSalon`

## Product (E-commerce)

```json
{
  "@type": "Product",
  "name": "Required",
  "image": "Required",
  "description": "Required",
  "sku": "Required",
  "brand": "Required",
  "offers": {
    "@type": "Offer",
    "price": "Required",
    "priceCurrency": "Required",
    "availability": "Required",
    "seller": "Recommended",
    "shippingDetails": "Recommended",
    "returnPolicy": "Recommended"
  },
  "aggregateRating": "Recommended",
  "review": "Recommended"
}
```

## Service

```json
{
  "@type": "Service",
  "name": "Required",
  "description": "Required",
  "provider": "Required",
  "areaServed": "Required",
  "offers": "Required (pricing)",
  "serviceType": "Recommended",
  "termsOfService": "Recommended"
}
```

## Agent-Critical vs SEO-Only Properties

| Property | SEO Value | Agent Value | Notes |
|----------|-----------|-------------|-------|
| price | High | Critical | Agent needs for comparison |
| availability | Medium | Critical | Agent won't recommend unavailable |
| openingHours | Medium | Critical | Agent checks before recommending |
| acceptsReservations | Low | Critical | Determines actionability |
| telephone | Low | High | Fallback action path |
| geo (lat/lng) | Medium | Critical | Distance calculation |
| paymentAccepted | Low | High | Agent transaction planning |
