# SmartFace Attendance — Initial Audit

**Date:** 2026-08-28
**Phase:** 1 / 10
**Status:** Audit of existing prototype complete. Multiple **P0 security vulnerabilities** found. See section 8 for full details and the fix status.

---

## 1. Executive Summary

SmartFace is an existing attendance-management prototype with four components (FastAPI backend, a separate AI face-recognition service, a React admin dashboard, and a Flutter kiosk app). It is **not production-ready**. The audit uncovered:

- **5 P0 security vulnerabilities** (unauthenticated register/checkin/checkout/face-recognition, public biometric serving, open CORS, weak hardcoded credentials).
- **Missing `/reports/*` router** (frontend called it, backend had none → 404 / 200-null).
- **No rate limiting / body-size limits** (DoS exposure).
- Face recognition is a **hand-rolled Pillow heuristic** (not real face recognition) — a core feature that does not actually recognize faces.
- ERP employee XML export **crashed** (referenced model fields that don't exist).
- Redundant/multiple deployment paths (root `Dockerfile` + `render.yaml` + `docker-compose.yml`) that disagree with each other.

A full set of security/QA code fixes has been **authored and applied to source** (uncommitted) per this audit; the live deployment still runs the old, vulnerable build.

---

## 2. System Overview

### 2.1 Architecture

```
frontend_kiosk (Flutter) ──► backend-api (FastAPI) ──► PostgreSQL (Supabase/Neon)
                                      │
frontend-admin (React) ───────────────┤
                                      ├─► ai-service (FastAPI, face recognition) [separate]
                                      ├─► storage/ (face images, embeddings)
                                      └─► Qdrant (vector DB, ai-service only, optional)
```

### 2.2 Components

| Component | Tech | Role | Status |
|-----------|------|------|--------|
| `backend-api` | FastAPI, SQLAlchemy (async), Alembic, asyncpg | Core REST API + admin seeding + SPA serving | Deployed on Render as `smartface-attendance-7ygu.onrender.com` |
| `ai-service` | FastAPI, OpenCV, Qdrant | Standalone face-detect/enroll/recognize/liveness | Present in repo; **not deployed**; backend has its own inline face logic |
| `frontend-admin` | React, TypeScript, MUI | Admin dashboard | Build artifacts expected at `backend-api/admin-dist` |
| `frontend_kiosk` | Flutter | Kiosk face-capture + checkin/checkout | Android APK built |
| `infrastructure` | Docker, Nginx, Redis | (per README) | Directory empty; config lives at root instead |

---

## 3. Environment / Deployment Facts

- **Live backend:** `https://smartface-attendance-7ygu.onrender.com` — runs an **OLD build** matching current source routers (no `/reports/*`; un-secured endpoints).
- **Login:** `admin@smartface.com` / `Admin123!` works on both live and local.
- **Database:** Supabase project `vtmqttyxtmohrtvrceqj` (PostgreSQL). Production DB has **20 employees (EMP001–EMP020) fully loaded** (extras stored as JSON in the `notes` field) and departments Production/Quality/Maintenance/HR/Accounts/Stores/Admin.
- Local dev DB (`backend-api/.env`) has different data (0 employees) → **data-discrepancy root cause still unresolved** but user chose to use the live server as source of truth.
- **Renderer:** 3 deployment definitions exist that disagree — root `render.yaml`, `backend-api/render.yaml` (the one actually used: `smartface-api`), and `docker-compose.yml` + root `Dockerfile`. **This is a production blocker** (see §8.6).

---

## 4. Features Present (as-built)

- Auth: login, refresh, register, `/auth/me`.
- Departments CRUD; Employees CRUD with search/filter/pagination; face-enrollment flag.
- Face enrollment, recognize, verify, duplicate-check, recognition logs (all inline, Pillow-based).
- Attendance checkin/checkout, daily records, logs, stats.
- ERP integration: config CRUD, sync, employee export (XML) — bridging to an external ERP.
- Reports: **NEW** module added (summary/employee/department) — previously missing.
- Role-based access (roles table, `SUPER_ADMIN`, `HR_ADMIN`, etc.).
- Audit logs, system settings, holidays, leave types, report exports, unknown-face events (tables exist; limited surfaced API).
- Admin SPA static serving + history fallback.

---

## 5. Codebase Inventory (backend-api)

### 5.1 Routers (`app/api/v1/`)
| File | Prefix | Notes |
|------|--------|-------|
| `auth.py` | `/auth` | login, refresh, register, me |
| `departments.py` | `/departments` | CRUD (mutations not admin-gated) |
| `employees.py` | `/employees` | CRUD (mutations not admin-gated) |
| `attendance.py` | `/attendance` | checkin/checkout/logs/stats/today |
| `faces.py` | `/faces` | enroll/recognize/verify/duplicate/image/logs |
| `erp.py` | `/erp` | config + export |
| `reports.py` | `/reports` | **NEW** — summary/employee/department |

### 5.2 Models (`app/models/`)
`user`, `role`, `department`, `employee`, `attendance`, `attendance_log`, `audit_log`, `face_profile`, `system_setting`, `holiday`, `leave_type`, `report_export`, `erp_config` (+`erp_sync_logs`), `unknown_face_event`.

### 5.3 Core / Services
- `core/config.py` — settings, CORS, rate limits, admin bootstrap, body-size cap.
- `core/security.py` — bcrypt, JWT, `get_current_user`, `require_admin`.
- `core/database.py` — async engine, `_force_ipv4()` helper (prior work, unverified).
- `services/face_service.py` — **Pillow-only heuristic embedding** (not real face recognition).
- `services/erp_integration.py` — XML export, `employee_to_xml` fixed.

---

## 6. Bugs Found (by category)

| # | Severity | Bug | Status |
|---|----------|-----|--------|
| 1 | **Critical** | `/auth/register` public + arbitrary `role_id` → privilege escalation | **Fixed in source** |
| 2 | **Critical** | `/attendance/checkin` & `/checkout` unauthenticated | **Fixed in source** |
| 3 | **Critical** | `/faces/recognize`, `check-duplicate`, `verify` public | **Fixed in source** |
| 4 | **Critical** | `/faces/image/{code}/{file}` public biometric serving | **Fixed in source** |
| 5 | **High** | CORS echoes any origin (`["*"]` default + `allow_credentials=True` conflict) | **Fixed in source** |
| 6 | **High** | No rate limiting on login (brute force) | **Fixed in source** (login) |
| 7 | **High** | No request body-size limit (DoS) | **Fixed in source** |
| 8 | **High** | Hardcoded weak `Admin123!` seed + `postgres:password` default | **Fixed in source** |
| 9 | **High** | `/erp/export/employees` 500 (XML referenced `emp.email`/`designation`/`date_of_joining`) | **Fixed in source** |
| 10 | **High** | `/reports/*` router missing → N/A/404 for frontend | **Fixed in source** (reports.py added) |
| 11 | Medium | Validation error codes inconsistent (400 vs 422) | **Fixed in source** (schemas) |
| 12 | Medium | No payload/enum validation on several inputs | **Partially fixed** |
| 13 | Medium | Employee/Department **mutations** only require `get_current_user`, not admin | **Open** (Phase 2) |
| 14 | Medium | No pagination consistency / no ordering guarantees | Open |
| 15 | Low | `department_id`/`employee_id` filter invalid UUID silently ignored (`pass`) | Open |
| 16 | Low | Faces stored as base64 in DB (`face_image_data` Text) — bloat | Open (Phase 5) |

---

## 7. Missing Features (per master prompt)

- **Real-time dashboard/notifications** (WebSocket/polling absent).
- **Actual face recognition** — current Pillow heuristic is not reliable.
- **Leave/absence workflows**, holiday calendar enforcement in attendance.
- **Full reporting** (only summary/employee/department added; no export to file, no scheduled reports).
- **Audit-trail wired through mutations** (table exists, not populated).
- **Unknown-face / liveness pipeline** (ai-service has it, not integrated).
- **RBAC enforcement across all mutation endpoints** (Phase 2).
- **Backup/restore, observability, structured logging.**

---

## 8. Production Blockers

### 8.1 Security (P0) — mitigation authored, not deployed
Endpoints were publicly reachable; fixes exist in working tree (uncommitted). **Blocked on deploy (Phase 9).**

### 8.2 Face recognition is not real
`face_service.py` produces a hand-crafted normalized-grayscale histogram, not a neural embedding. Matches are weak/false-positive prone. **Planned:** switch to InsightFace/ArcFace in the backend to actually enable "face is not properly sensing" fix (Phase 5).

### 8.3 Two face "services" with drift
`ai-service` (OpenCV/InsightFace/Qdrant) is not deployed and not referenced by the current backend despite the repo README describing it. Decide the single source of truth (Phase 5).

### 8.4 Conflicting deployment configs
Root `Dockerfile`/`render.yaml`/`docker-compose.yml` vs `backend-api/render.yaml` vs `ai-service/Dockerfile` describe different services, ports, DBs, and CORS. Must consolidate (Phase 9).

### 8.5 Data-source ambiguity
Local `.env` DB vs Supabase/Render DB show different data; unresolved root cause. Live is now source of truth. Cleanup of 3 legacy employee codes + 2 stray departments offered, not authorized.

### 8.6 IPv4 connectivity / Render deploy failure
Prior `OSError: [Errno 101] Network is unreachable` during Render deploy and the `_force_ipv4()` fix remain **unverified/uncommitted** (Phase 9).

---

## 9. DB Issues

- Tables created via Alembic `001_initial.py`; employees/departments seeded manually on live.
- `FaceProfile.face_image_data`/`embedding_data` as unbounded `Text` — store binaries/embeddings via object storage/vector DB instead.
- No indexes on frequent filter columns beyond PK/unique (search by `full_name`, `employee_code` ILIKE will be slow at scale).
- `notes` abused as a JSON bag-of-extras for employees (design/UX debt).

---

## 10. Performance Issues

- `faces.py` loads **all** face profiles and recomputes matching in Python on every call — O(n) full DB read per request; will not scale.
- Sequential per-log employee lookups in `recognize/logs` enrichment (N+1).
- No caching, no connection pooling tuning, no migration of face data to vector DB.
- Static SPA served by the same process as the API.

---

## 11. Recommended Direction

1. **Phase 2 (Foundation):** enforce RBAC on all mutations; structured logging; centralized error handling; input/validation hardening.
2. **Phase 3 (Core):** wire audit logging to mutations; leave/holiday workflows; correct attendance rules (late/checkout/cooldown).
3. **Phase 5 (AI):** replace Pillow face heuristic with InsightFace; clean base64 storage; define one face service.
4. **Phase 6 (Reporting):** expand reports + file export + scheduled jobs.
5. **Phase 9 (DevOps):** consolidate deployment; secrets via env; migrations in CI; deploy the hardened build; re-test IPv4 fix.
6. **Phase 10 (Final audit):** re-run full QA + security audit before declaring production-ready.

---

## 12. Phase 1 Completion Checklist

- [x] Full repo structure mapped (backend, ai-service, frontend-admin, frontend_kiosk).
- [x] All backend routers/models/schemas/services read & assessed.
- [x] Deployment files (Dockerfile(s), render.yaml, docker-compose, .env.example) reviewed.
- [x] Frontend API contract (`api.ts`) & kiosk flow confirmed.
- [x] `/docs/INITIAL_AUDIT.md` authored (this file).
- [x] `/docs/ARCHITECTURE.md` (target of Phase 2).
- [x] `/docs/PRODUCTION_READINESS.md` (target of Phase 10).

> **Next action:** begin Phase 2 — Foundation (RBAC on mutations, logging, validation). Existing uncommitted security fixes serve as the Phase 2 seed.
