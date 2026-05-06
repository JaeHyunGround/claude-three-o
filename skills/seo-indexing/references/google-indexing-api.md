<!-- Updated: 2026-05-04 -->
# Google Indexing API Reference

## Overview

The Indexing API allows site owners to notify Google about URL changes.
Limited to pages with `JobPosting` or `BroadcastEvent` schema by default,
but can be used for general indexing with Search Console verification.

## Authentication

Requires Google Service Account with Indexing API enabled.
Service account email must be added as owner in Search Console.

## Endpoints

Base URL: `https://indexing.googleapis.com/v3/urlNotifications`

### Publish (notify about URL)
```
POST /urlNotifications:publish
{
  "url": "https://example.com/page",
  "type": "URL_UPDATED"  // or "URL_DELETED"
}
```

### Get Status
```
GET /urlNotifications/metadata?url=https://example.com/page
```

## Rate Limits

| Limit | Value |
|-------|-------|
| Requests per day | 200 (default) |
| Batch requests | Up to 100 URLs per batch |
| Quota increase | Request via Google Cloud Console |

## Notification Types

| Type | When to use |
|------|-------------|
| `URL_UPDATED` | New page or significant content change |
| `URL_DELETED` | Page permanently removed (410/404) |

## Integration Notes

- Complementary to sitemap submission, not a replacement
- Does not guarantee indexing, only prioritizes crawling
- Check results via Google Search Console URL Inspection
- Store service account credentials at `~/.config/three-o/google_service_account.json`
