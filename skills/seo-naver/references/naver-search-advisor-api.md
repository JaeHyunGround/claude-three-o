<!-- Updated: 2026-05-04 -->
# Naver Search Advisor API Reference

## Overview

Naver Search Advisor (서치어드바이저) is Naver's equivalent of Google Search Console.
URL: https://searchadvisor.naver.com/

## Key Functions

| Function | Endpoint | Description |
|----------|----------|-------------|
| Site verification | Web console | Verify site ownership (HTML tag, file, DNS) |
| Sitemap submit | Web console / API | Submit XML sitemap for Naver indexing |
| URL submit | Web console | Request individual URL indexing |
| Crawl diagnostics | Web console | View crawl errors and blocked resources |
| Search analytics | Web console | Query impressions and clicks on Naver |

## Naver Webmaster API

Base URL: `https://searchadvisor.naver.com/api/`

Authentication: Naver Developer API credentials required.

| API | Method | Purpose |
|-----|--------|---------|
| Site list | GET | List verified sites |
| Crawl errors | GET | Retrieve crawl error reports |
| Index status | GET | Check URL indexing status |

## Integration Notes

- API access requires Naver Developer account registration
- Rate limits: typically 1000 requests/day
- Data freshness: updated daily (not real-time like GSC)
- Korean-language documentation only for most endpoints
- Store credentials at `~/.config/three-o/naver_credentials.json`
