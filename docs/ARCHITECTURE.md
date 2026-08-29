# SmartFace Attendance — Architecture

**Date:** 2026-08-28
**Phase:** 2 / 10
**Status:** Foundation (RBAC/logging/validation/error-handling) implemented. This doc records the intended production architecture.

---

## 1. Component Overview

```
             ┌────────────────────────────┐
             │   frontend_kiosk (Flutter) │
             │   face capture, buttons    │
             └─────────────┬──────────────┘
                           │ HTTPS JSON (base64 image)
                           ▼
┌──────────────────────────────────────────────────────┐
│                backend-api (FastAPI)                  │
│  ├─ app/api/v1   routers: auth, departments,          │
│  │                employees, attendance, faces,       │
│  │                erp, reports                        │
│  ├─ app/core     config, security, database, logging  │
│  ├─ app/models   SQLAlchemy ORM (17 tables)           │
│  ├─ app/schemas  Pydantic validation                  │
│  ├─ app/services face_service, erp_integration        │
│  ├─ static admin-dist (React SPA)                     │
│  └─ storage/     uploaded face images/embeddings      │
└───────────┬───────────────────────────────────┬───────┘
            │                                   │
            ▼                                   ▼
    PostgreSQL (Supabase/Neon)          optional Qdrant vector DB
```

## 2. Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `backend-api` | Single FastAPI service: REST API, auth, RBAC, business logic, file storage, SPA hosting. The **single deployable** backend. |
| `frontend-admin` | React admin SPA (built → `backend-api/admin-dist`, served by backend). |
| `frontend_kiosk` | Flutter app (Android APK) for the physical kiosk terminal. |
| `ai-service` | **Deprecated / not deployed.** Legacy separate face-recognition service (OpenCV/Qdrant). The active backend performs face logic in-process via `face_service.py`. To be either removed or consolidated in Phase 5. |
| Postgres | Persistence. |
| Qdrant / object storage | Future vector store / blob storage (Phase 5). |

## 3. Layer Design (backend-api)

- **API layer** (`app/api/v1/`): HTTP contracts. Dependencies from `app/core/security`.
  - Read endpoints → `get_current_user`.
  - Mutation endpoints (create/update/delete/enroll/push) → `require_admin` (SUPER_ADMIN, HR_ADMIN).
  - `auth/register` → `require_admin` (only admins create users).
- **Core layer** (`app/core/`):
  - `config.py` — env-driven settings; strong `SECRET_KEY` generation; CORS allowlist; rate-limit + body-size caps.
  - `security.py` — bcrypt, JWT access/refresh, `get_current_user`, `require_admin`.
  - `database.py` — async engine w/ IPv4 fallback, session dependency.
  - `logging_config.py` — JSON structured logging.
- **Models** (`app/models/`): SQLAlchemy ORM; migrations via Alembic (`alembic/versions/`).
- **Schemas** (`app/schemas/`): Pydantic validation — enums for status/event types, `EmailStr`, numeric bounds.
- **Services** (`app/services/`): `face_service` (Pillow heuristic, to be upgraded to InsightFace in Phase 5), `erp_integration`.

## 4. Middleware Stack (app/main.py, order)

1. `CORSMiddleware` — explicit origin allowlist (no wildcard with credentials).
2. `BodySizeLimitMiddleware` — reject bodies > `MAX_REQUEST_BODY_BYTES` (413).
3. `LoginRateLimitMiddleware` — per-IP throttling on `/auth/login` (429 + `Retry-After`).
4. `RequestLogMiddleware` — structured JSON request logging (method/path/status/ip/duration).

## 5. Security Model

- Auth: JWT bearer (`ACCESS_TOKEN_EXPIRE_MINUTES=30`, refresh `7d`).
- Roles: `SUPER_ADMIN`, `HR_ADMIN`, `VIEWER`; admin set = {SUPER_ADMIN, HR_ADMIN} (or the seeded admin email).
- Data protection: biometric images/embeddings gated behind `get_current_user`; mutation write paths admin-gated.
- Secrets: only via env (`SECRET_KEY`, `DATABASE_URL`, Supabase keys, `ADMIN_INITIAL_PASSWORD`).

## 6. Deployment (target)

Consolidate in Phase 9 to a **single** containerized FastAPI service:
- Build React SPA → `backend-api/admin-dist` at build time.
- Alembic migrations run in the start command.
- Env-driven secrets from the platform (Render env vars / secrets).
- One `render.yaml` / `Dockerfile` source of truth (reconciles the current conflicting root/backend/ai definitions).

## 7. Key Technical Decisions

- Face verification happens in-process (synchronous, Pillow now → InsightFace later); no Qdrant dependency in the hot path today.
- Images stored as base64 in DB (`face_image_data`) — acceptable short-term; move to object storage in Phase 5.
- All mutations written idempotently; no destructive SQL executed by the app without an admin token.

## 8. Flow: Check-in (kiosk)

1. Kiosk captures face → POST `/api/v1/faces/recognize` (base64, Bearer).
2. Backend encodes image, finds best embedding match, returns employee.
3. Kiosk (or backend) POST `/api/v1/attendance/checkin` → Attendance + AttendanceLog rows.
4. Frontend dashboards read `/api/v1/attendance/*`, `/api/v1/reports/*`.

## 9. Flow: Employee + Face Enrollment (admin)

1. Admin creates employee (`POST /api/v1/employees`).
2. Admin enrolls face (`POST /api/v1/faces/enroll`) → embedding + image stored; `face_enrolled=true`.
3. Duplicate detection via `/api/v1/faces/check-duplicate`.

## 10. Phase 2 Deliverables

- [x] RBAC on all mutations (employees, departments, erp, faces enroll/delete).
- [x] Structured JSON logging (request + startup/seed).
- [x] Input/validation hardening (EmailStr, enums, numeric bounds, string lengths).
- [x] Body-size limit + login rate limit (from Phase 1 fixes, wired in).
- [x] Architecture documentation (this file).
- [ ] Error-handling consistency pass (invalid-UUID filter behavior) — deferred/advisory.
