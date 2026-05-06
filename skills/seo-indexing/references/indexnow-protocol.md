<!-- Updated: 2026-05-04 -->
# IndexNow Protocol Reference

## Overview

IndexNow allows websites to notify search engines about URL changes instantly,
rather than waiting for crawlers to discover changes.

## Supported Engines

| Engine | IndexNow Support | Endpoint |
|--------|-----------------|----------|
| Bing | Yes | `https://www.bing.com/indexnow` |
| Yandex | Yes | `https://yandex.com/indexnow` |
| Naver | Yes | `https://searchadvisor.naver.com/indexnow` |
| Google | No | Uses Indexing API instead |

## Setup

1. Generate API key (any UUID-like string)
2. Place key file at `https://domain.com/{key}.txt`
3. Key file content: the key string itself

## API Usage

### Single URL
```
GET https://www.bing.com/indexnow?url={url}&key={key}
```

### Batch URLs (POST)
```json
POST https://www.bing.com/indexnow
{
  "host": "www.example.com",
  "key": "your-key",
  "urlList": [
    "https://www.example.com/page1",
    "https://www.example.com/page2"
  ]
}
```

Maximum 10,000 URLs per batch request.

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | URL submitted successfully |
| 202 | Accepted, pending processing |
| 400 | Invalid request |
| 403 | Key not valid |
| 422 | URL doesn't match host |
| 429 | Too many requests |
