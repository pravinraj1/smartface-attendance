# SmartFace Attendance — Production Readiness

**Date:** 2026-08-29
**Phase:** 10 / 10
**Status:** Code-wide hardening complete and committed. **Live go-live is gated on a successful Render deploy** of the latest commit (Manual Deploy required; the live service still runs a pre-hardening build at the time of writing).

---

## 1. Sign-off Criteria

| Criterion | Status |
|-----------|--------|
| P0 security findings from `INITIAL_AUDIT.md` fixed in source | Fixed (all 5) |
| RBAC enforced on all mutations | Done (admin-only mutations; authenticated self-service attendance) |
| Audit trail on mutations | Done (employee, department, face-enroll) |
| Auth hardening (JWT type separation, refresh revocation, password policy, SSRF guard) | Done |
| Rate limiting / body-size caps on login | Done (per-IP failed-login; Content-Length check) |
| Requirements build on bare `python:3.12` Docker image | Fixed (heavy face deps moved to optional file) |
| Automated test suite | **14 passed** |
| Endpoint contract smoke sweep (45 routes) | Verified (Phase 8) |
| `/docs/PRODUCTION_READINESS.md` | This document |
| **Live deployment of hardened build** | **PENDING — manual deploy + verification** |

---

## 2. Security Posture

### 2.1 Authentication & Authorization
- bcrypt password hashing (passlib + bcrypt 4.2.0).
- Access tokens (`type=access`, 30 min) and refresh tokens (`type=refresh`, 7 days) are **distinct**; refresh tokens are rejected if passed as bearer credentials (`core/security.py`).
- Refresh-token revocation via per-user `refresh_token_version` (logout increments; stale tokens rejected).
- New passwords enforced ≥8 chars with letter+digit (`validate_password_strength`).
- RBAC: mutations require `SUPER_ADMIN`/`HR_ADMIN` via `require_admin`; attendance logs/self-service are authenticated.
- Sign-in seeded by env (`ADMIN_EMAIL`/`ADMIN_INITIAL_PASSWORD`), auto-generated if not set.

### 2.2 Network & Input Hardening
- CORS scoped to explicit origins (Render + localhost dev); no wildcard-with-credentials.
- Login rate limit (default 10 failed attempts / 60 s per IP) with `Retry-After`; real client IPs honored behind Render LB (`--proxy-headers --forwarded-allow-ips=*`).
- Request body-size cap (413) via Content-Length check.
- SSRF guard on outbound ERP/webhook URLs (private/loopback/link-local rejected).
- Static-file serving path-traversal guard: only files under `admin-dist` are served.
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: no-referrer`.
- Docs/OpenAPI disabled in production (`DOCS_ENABLED=false`).
- `.env` excluded from image (`.dockerignore`) and repo (`.gitignore`); secrets only via Render env vars (`SECRET_KEY` generated, `DATABASE_URL` synced from dashboard).

### 2.3 Known Limitations
- Body-size cap relies on `Content-Length`; chunked-transfer (no length header) is not capped. Acceptable given trusted kiosk/admin clients.
- Rate limiter is in-memory (per instance). Adequate for the single-instance Render service; would need Redis or a DB-backed store for horizontal scaling.
- `require_admin` retains an escape hatch for the seeded `ADMIN_EMAIL` when no role is assigned (operational convenience; keep the seed email private).

---

## 3. Data & Schema
- Alembic migrations `001_initial`, `002_add_user_refresh_token_version`; local dev DB (Supabase) migrated — refresh-revocation exercised by tests.
- Tables: users, roles, departments, employees, attendance, attendance_logs, audit_logs, face_profiles, erp_config(+sync logs), system_settings, holidays, leave_types, report_exports, unknown_face_events.
- Backup/source of truth: managed PostgreSQL (Supabase/Neon) with provider-managed backups + point-in-time restore within retention. No self-managed backups required.
- **Deployment caution:** the target `DATABASE_URL` must have migrations applied (especially `users.refresh_token_version` and seeded `roles`) before the hardened build is switched to it; otherwise login/RBAC will fail.

---

## 4. Monitoring & Operations
- `/health` returns `{"status":"healthy","version":...}` (DB-independent, so it reflects process health, not DB health).
- Structured JSON request logs (method, path, status, duration, client IP) to stdout — visible in Render logs.
- Render Events/Deploys tab shows build/start failures; container restarts on health-check failure.

---

## 5. Deployment Runbook (Render)
1. Push to `main` (auto-deploy is **off** — must be manual).
2. Console → `smartface-attendance` → **Manual Deploy → Deploy latest commit**.
3. Env vars required: `DATABASE_URL` (dashboard, `sync: false`), `SECRET_KEY` (generated), `STORAGE_PATH=/app/storage`, `CORS_ORIGINS` (explicit list), `DOCS_ENABLED=false`.
4. Verify: `GET https://smartface-attendance-7ygu.onrender.com/health` → 200; log in via `/api/v1/auth/login`; spot-check `/api/v1/audit-logs` and `/api/v1/reports/*` (404/401 on the old build).
5. If the build fails, read the failing step from the Events tab and feed it back for a fix.

> Note: with `DOCS_ENABLED=false`, `/openapi.json`, `/docs`, `/redoc` are disabled in production; verify the route contract by hitting endpoints directly.

---

## 6. Legacy / Out-of-Scope Notes
- `ai-service` and Qdrant remain unused by the backend; backend performs face embedding via InsightFace when the optional deps are installed, else degrades gracefully (enroll/recognize return "no face detected"; PIN/code workflows unaffected).
- `docker-compose.yml` and `backend-api/render.yaml`/`Dockerfile` are legacy/alternate paths; root `Dockerfile` + `render.yaml` are the canonical deployment.
- Known debts tracked for a future phase: N+1 enrichment in `/faces/recognize/logs`, O(n) face matching per request, base64 face storage in DB, no scheduled report jobs.

**Sign-off: code hardened; deploy pending live verification before declaring the service production-ready.**