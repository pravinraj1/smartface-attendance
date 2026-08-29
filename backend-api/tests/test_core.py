"""Core business-flow, reporting, and ERP-security tests."""
import uuid


def test_attendance_roundtrip(client, admin_headers, employee):
    assert employee is not None
    eid = employee["id"]

    ci = client.post(
        "/api/v1/attendance/checkin",
        json={"employee_id": eid, "confidence_score": 0.9},
        headers=admin_headers,
    )
    assert ci.status_code == 200, f"checkin failed: {ci.text}"
    assert ci.json()["action"] == "CHECK_IN"

    co = client.post(
        "/api/v1/attendance/checkout",
        json={"employee_id": eid, "confidence_score": 0.9},
        headers=admin_headers,
    )
    assert co.status_code == 200, f"checkout failed: {co.text}"
    assert co.json()["action"] == "CHECK_OUT"

    # double checkin must be rejected
    ci2 = client.post(
        "/api/v1/attendance/checkin",
        json={"employee_id": eid, "confidence_score": 0.9},
        headers=admin_headers,
    )
    assert ci2.status_code == 400

    # enriched attendance list has the record + names
    att = client.get(f"/api/v1/attendance?employee_id={eid}", headers=admin_headers)
    assert att.status_code == 200
    body = att.json()
    assert body["total"] >= 1
    assert any(a["employee_id"] == eid for a in body["attendance"])

    # live feed reflects the events
    live = client.get("/api/v1/attendance/logs/live", headers=admin_headers)
    assert live.status_code == 200
    assert live.json()["count"] >= 1


def test_reports_json(client, admin_headers, employee):
    assert employee is not None
    eid = employee["id"]

    emp_json = client.get(f"/api/v1/reports/employee/{eid}", headers=admin_headers)
    assert emp_json.status_code == 200

    dept = client.get(f"/api/v1/reports/department/{employee['department_id']}", headers=admin_headers)
    assert dept.status_code == 200
    assert dept.json()["total_employees"] >= 1

    summ = client.get("/api/v1/reports/summary", headers=admin_headers)
    assert summ.status_code == 200


def test_reports_csv(client, admin_headers, employee):
    assert employee is not None
    eid = employee["id"]

    r = client.get(f"/api/v1/reports/employee/{eid}?format=csv", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")

    rd = client.get(f"/api/v1/reports/department/{employee['department_id']}?format=csv", headers=admin_headers)
    assert rd.status_code == 200
    assert "attachment" in rd.headers.get("content-disposition", "")

    rs = client.get("/api/v1/reports/summary?format=csv", headers=admin_headers)
    assert rs.status_code == 200
    assert "attachment" in rs.headers.get("content-disposition", "")


def test_invalid_report_format_rejected(client, admin_headers, employee):
    r = client.get(f"/api/v1/reports/employee/{employee['id']}?format=exe", headers=admin_headers)
    assert r.status_code == 422


def test_erp_config_get_requires_auth(client):
    assert client.get("/api/v1/erp/config").status_code == 403


def test_erp_ssrf_rejected(client, admin_headers):
    bad = client.post(
        "/api/v1/erp/config",
        json={"erp_url": "http://localhost:8080", "webhook_url": "http://127.0.0.1/x"},
        headers=admin_headers,
    )
    assert bad.status_code == 400
    bad2 = client.post(
        "/api/v1/erp/config",
        json={"erp_url": "http://192.168.1.5", "webhook_url": "http://10.0.0.1/x"},
        headers=admin_headers,
    )
    assert bad2.status_code == 400


def test_erp_save_redact_preserve(client, admin_headers, db_call):
    """Saving redacted sentinels must not overwrite the real secret."""
    from sqlalchemy import select
    from app.models.erp_config import ERPConfig

    r = client.post(
        "/api/v1/erp/config",
        json={
            "erp_url": "https://example.com",
            "api_key": "real-secret-XYZ",
            "webhook_secret": "real-wh-123",
        },
        headers=admin_headers,
    )
    assert r.status_code == 200

    # GET must be redacted
    got = client.get("/api/v1/erp/config", headers=admin_headers).json()
    assert got["api_key"] == "***redacted***"
    assert got["webhook_secret"] == "***redacted***"

    # re-save with sentinel -> keep
    r2 = client.post(
        "/api/v1/erp/config",
        json={
            "erp_url": "https://example.com",
            "api_key": "***redacted***",
            "webhook_secret": "***redacted***",
        },
        headers=admin_headers,
    )
    assert r2.status_code == 200

    async def _inspect_and_clean(db):
        cfg = (await db.execute(select(ERPConfig))).scalars().first()
        assert cfg is not None
        assert cfg.api_key == "real-secret-XYZ", f"secret overwritten: {cfg.api_key}"
        assert cfg.webhook_secret == "real-wh-123"
        await db.delete(cfg)
        await db.commit()
    db_call(_inspect_and_clean)


def test_rbac_viewer_denied_bulk_export(client, admin_headers, db_call):
    """Create a VIEWER, confirm bulk PII reports are 403, cleanup."""
    from sqlalchemy import select
    from app.models.user import User

    email = f"rbac_{uuid.uuid4().hex[:8]}@t.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "RBAC Viewer",
            "password": "RbacPass1",
            "role_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13",
        },
        headers=admin_headers,
    )
    assert reg.status_code == 200, f"register failed: {reg.text}"

    lg = client.post("/api/v1/auth/login", json={"email": email, "password": "RbacPass1"})
    assert lg.status_code == 200
    vh = {"Authorization": f"Bearer {lg.json()['access_token']}"}

    assert client.get("/api/v1/erp/export/employees?format=json", headers=vh).status_code == 403
    assert client.get("/api/v1/erp/export/attendance?format=json", headers=vh).status_code == 403
    assert client.get("/api/v1/erp/sync-logs", headers=vh).status_code == 403
    # config GET still allowed but redacted when present
    cfg_resp = client.get("/api/v1/erp/config", headers=vh)
    assert cfg_resp.status_code == 200

    async def _cleanup(db):
        u = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if u:
            await db.delete(u)
            await db.commit()
    db_call(_cleanup)
