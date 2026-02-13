# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GEX Corporation API — a Django REST Framework backend for processing business events (cart abandonment, purchases, leads) from multiple e-commerce platforms (Hotmart, Kiwify, Braip, Eduzz, Tray). Integrates with Facebook Conversion API (CAPI) and is designed to receive raw webhook data from n8n workflows. All documentation and code comments are in Portuguese.

## Commands

```bash
# Development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Tests (Django test runner, currently empty test suite)
python manage.py test

# Static files (for admin panel)
python manage.py collectstatic --noinput

# Docker
docker-compose up -d --build
```

**Production** runs via Gunicorn on Railway.app (`gunicorn core.wsgi:application`). The `PORT` env var is set by Railway.

## Architecture

**Layered service architecture** within a single Django app (`orders`):

```
Webhook request → views.py (_handle_webhook) → services.py (process_event)
                                                  ├─ data_transformers.py (normalize + detect platform)
                                                  ├─ models.py (upsert Lead, create CapiEvent/Order)
                                                  └─ FacebookCAPIService.send()
```

### Key files

- **`core/settings.py`** — Django config, DB credentials, Facebook CAPI tokens, DRF/Spectacular settings
- **`core/urls.py`** — API routing under `/api/v1/`
- **`orders/views.py`** — ViewSets (Order, Lead, CapiEvent) + webhook endpoint functions. `_handle_webhook()` is the centralized webhook handler
- **`orders/services.py`** — `process_event()` orchestrates: normalize data → upsert lead → create event → send to Facebook CAPI. `FacebookCAPIService` handles CAPI requests with SHA256 hashing
- **`orders/data_transformers.py`** — `PlatformDetector` auto-detects source platform from raw payload. `DataNormalizer` standardizes emails, phones (+55 format), names, currency. Platform-specific transformers (Hotmart, Kiwify) + `UniversalTransformer` fallback
- **`orders/models.py`** — Three models, all with UUID PKs and `managed = False` (schema managed externally via Supabase): `Lead`, `Order`, `CapiEvent`
- **`orders/serializers.py`** — DRF ModelSerializers for each model

### Database

PostgreSQL via Supabase Pooler. Models use `managed = False` — do NOT create Django migrations that alter table schema. The database tables are managed externally.

### API Endpoints

- `POST /api/v1/webhook/` — Universal webhook (auto-detects event type and platform)
- `POST /api/v1/webhook/cart-abandonment/` | `purchase-approved/` | `lead/` — Type-specific webhooks
- `/api/v1/orders/`, `/api/v1/leads/`, `/api/v1/capi-events/` — CRUD ViewSets
- `GET /api/v1/health/` — Health check
- `GET /api/docs/` — Swagger UI, `GET /api/redoc/` — ReDoc

### Response format

All webhook responses follow: `{"status": "success|error", "message": "...", "data": {...}}`

## Code Conventions

- Portuguese naming in business logic (variable names, comments, response messages)
- snake_case functions/variables, PascalCase classes
- Upsert pattern via `update_or_create` for idempotent lead handling
- Event deduplication via `event_id` field on CapiEvent
- Phone normalization target: `+55XXXXXXXXXXX`

## Important Notes

- Credentials (DB password, Facebook token) are hardcoded in `settings.py` — not using env vars yet
- `DEBUG = True` and `CORS_ALLOW_ALL_ORIGINS = True` in settings
- No authentication configured on API endpoints
- `orders/tests.py` exists but is empty — no test coverage
