"""3-shift + overtime feature tests.

Coverage:
- OT & lateness calculation unit tests (incl. overnight + partial + early)
- Shift CRUD + validation via API
- Shift assignment to an employee via API
- Shift-aware checkin/checkout roundtrip (OT fields populated on the record)
- Reports expose OT + shift fields
"""
import uuid
from datetime import datetime, date, time

from app.models.shift import Shift
from app.api.v1.attendance import (
    _compute_ot,
    _apply_ot,
    _is_overnight,
    _compute_late_minutes,
    _standard_minutes,
)

SHIFT_8 = Shift(standard_hours=8)
SHIFT_9 = Shift(standard_hours=9)
SHIFT_OVERNIGHT = Shift(
    shift_name="Overnight",
    start_time=time(22, 0),
    end_time=time(6, 0),
    standard_hours=8,
    grace_period=0,
)


def _shift(start, end, std=8, grace=0):
    return Shift(
        shift_name=f"S{start:%H%M}-{end:%H%M}",
        start_time=start,
        end_time=end,
        standard_hours=std,
        grace_period=grace,
    )


# ---------------- OT unit tests (Feature 20 Test 1-8) ----------------

def test_ot_exactly_8h():
    # 09:00 -> 17:00 = 8h ; OT = 0
    rec = type("R", (), {"check_in": datetime(2026, 9, 4, 9, 0)})()
    _apply_ot(rec, SHIFT_8, datetime(2026, 9, 4, 17, 0))
    assert rec.total_work_minutes == 480
    assert rec.normal_work_minutes == 480
    assert rec.overtime_minutes == 0


def test_ot_9h():
    _ = type("R", (), {"_": 1})()
    n, ot = _compute_ot(SHIFT_8, 540)
    assert n == 480 and ot == 60


def test_ot_10h():
    n, ot = _compute_ot(SHIFT_8, 600)
    assert n == 480 and ot == 120


def test_ot_partial_9h30():
    n, ot = _compute_ot(SHIFT_8, 570)
    assert n == 480 and ot == 90


def test_ot_early_6h_no_negative():
    n, ot = _compute_ot(SHIFT_8, 360)
    assert n == 360 and ot == 0


def test_ot_respects_shift_standard_hours():
    # 9-hour shift -> 9h standard
    n, ot = _compute_ot(SHIFT_9, 600)
    assert n == 540 and ot == 60


def test_ot_zero_total():
    n, ot = _compute_ot(SHIFT_8, 0)
    assert n == 0 and ot == 0


# ---------------- Overnight shift tests (Feature 15, 20 Test 5-6) ----------------

def test_overnight_detection():
    assert _is_overnight(SHIFT_OVERNIGHT, SHIFT_OVERNIGHT.start_time, SHIFT_OVERNIGHT.end_time) is True
    assert _is_overnight(_shift(time(6, 0), time(14, 0)), time(6, 0), time(14, 0)) is False


def test_overnight_exact_8h_no_ot():
    n, ot = _compute_ot(SHIFT_OVERNIGHT, 480)
    assert n == 480 and ot == 0


def test_overnight_plus_ot_45m():
    n, ot = _compute_ot(SHIFT_OVERNIGHT, 525)
    assert n == 480 and ot == 45


def test_standard_minutes_default_and_shift():
    assert _standard_minutes(None) == 480
    assert _standard_minutes(SHIFT_9) == 540
    assert _standard_minutes(SHIFT_OVERNIGHT) == 480


# ---------------- Late tests (Feature 20 Test 7) ----------------

def test_late_shift_aware():
    sft = _shift(time(9, 0), time(17, 0), grace=0)
    today = date(2026, 9, 4)
    # check in 09:20 -> late
    late = _compute_late_minutes(datetime(2026, 9, 4, 9, 20), today, sft, sft.start_time, sft.end_time)
    assert late == 20
    # check in 09:00 -> not late
    late0 = _compute_late_minutes(datetime(2026, 9, 4, 9, 0), today, sft, sft.start_time, sft.end_time)
    assert late0 == 0


def test_late_grace_period():
    sft = _shift(time(9, 0), time(17, 0), grace=15)
    today = date(2026, 9, 4)
    # within grace -> not late
    assert _compute_late_minutes(datetime(2026, 9, 4, 9, 10), today, sft, sft.start_time, sft.end_time) == 0
    # beyond grace -> late
    assert _compute_late_minutes(datetime(2026, 9, 4, 9, 20), today, sft, sft.start_time, sft.end_time) == 5


# ---------------- Shift CRUD / assignment / integration (live DB) ----------------

def test_shift_crud_and_validation(client, admin_headers):
    name = f"Shift_{uuid.uuid4().hex[:6]}"
    payload = {
        "shift_name": name,
        "start_time": "06:00:00",
        "end_time": "14:00:00",
        "standard_hours": 8,
        "grace_period": 0,
    }
    r = client.post("/api/v1/shifts", json=payload, headers=admin_headers)
    assert r.status_code == 201, f"create shift: {r.text}"
    sid = r.json()["id"]

    try:
        # invalid: identical start/end
        bad = client.post("/api/v1/shifts", json={
            "shift_name": f"{name}_bad",
            "start_time": "10:00:00",
            "end_time": "10:00:00",
            "standard_hours": 8,
        }, headers=admin_headers)
        assert bad.status_code == 400

        # invalid: negative standard hours
        bad2 = client.post("/api/v1/shifts", json={
            "shift_name": f"{name}_bad2",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "standard_hours": -1,
        }, headers=admin_headers)
        assert bad2.status_code == 422  # caught by Pydantic ge=0

        # duplicate name
        dup = client.post("/api/v1/shifts", json=payload, headers=admin_headers)
        assert dup.status_code == 400

        # get list + by id
        lst = client.get("/api/v1/shifts", headers=admin_headers)
        assert lst.status_code == 200
        assert any(s["id"] == sid for s in lst.json())

        one = client.get(f"/api/v1/shifts/{sid}", headers=admin_headers)
        assert one.status_code == 200
        assert one.json()["shift_name"] == name

        # update (enable/disable + times)
        upd = client.put(f"/api/v1/shifts/{sid}", json={
            "start_time": "07:00:00",
            "end_time": "15:30:00",
            "standard_hours": 8.5,
            "is_active": False,
        }, headers=admin_headers)
        assert upd.status_code == 200, f"update: {upd.text}"
        assert upd.json()["is_active"] is False
        assert float(upd.json()["standard_hours"]) == 8.5
    finally:
        client.delete(f"/api/v1/shifts/{sid}", headers=admin_headers)


def test_shift_assignment_to_employee(client, admin_headers, employee):
    assert employee is not None
    name = f"Assign_{uuid.uuid4().hex[:6]}"
    r = client.post("/api/v1/shifts", json={
        "shift_name": name,
        "start_time": "14:00:00",
        "end_time": "22:00:00",
        "standard_hours": 8,
        "grace_period": 0,
    }, headers=admin_headers)
    assert r.status_code == 201
    sid = r.json()["id"]

    try:
        assign = client.put(f"/api/v1/employees/{employee['id']}/shift", json={"shift_id": sid}, headers=admin_headers)
        assert assign.status_code == 200, f"assign: {assign.text}"
        assert assign.json()["shift_id"] == sid

        # assignment reflected on employee record
        emp = client.get(f"/api/v1/employees/{employee['id']}", headers=admin_headers).json()
        assert emp["shift_id"] == sid

        # unassign
        un = client.put(f"/api/v1/employees/{employee['id']}/shift", json={"shift_id": None}, headers=admin_headers)
        assert un.status_code == 200
        assert un.json()["shift_id"] is None
    finally:
        client.delete(f"/api/v1/shifts/{sid}", headers=admin_headers)


def test_shift_attendance_roundtrip_ot(client, admin_headers, employee):
    """Assign a shift, check in/out via the existing kiosk flow, and confirm the
    resulting attendance record carries shift + OT fields with total = normal + OT."""
    assert employee is not None
    name = f"Att_{uuid.uuid4().hex[:6]}"
    r = client.post("/api/v1/shifts", json={
        "shift_name": name,
        "start_time": "06:00:00",
        "end_time": "14:00:00",
        "standard_hours": 8,
        "grace_period": 0,
    }, headers=admin_headers)
    assert r.status_code == 201
    sid = r.json()["id"]

    try:
        client.put(f"/api/v1/employees/{employee['id']}/shift", json={"shift_id": sid}, headers=admin_headers)

        ci = client.post("/api/v1/attendance/checkin", json={"employee_id": employee["id"], "confidence_score": 0.9}, headers=admin_headers)
        assert ci.status_code == 200, f"checkin: {ci.text}"
        co = client.post("/api/v1/attendance/checkout", json={"employee_id": employee["id"], "confidence_score": 0.9}, headers=admin_headers)
        assert co.status_code == 200, f"checkout: {co.text}"

        att = client.get(f"/api/v1/attendance?employee_id={employee['id']}", headers=admin_headers).json()
        rec = next(a for a in att["attendance"] if a["employee_id"] == employee["id"])
        assert rec["shift_id"] == sid
        assert rec["total_work_minutes"] >= 0
        assert rec["normal_work_minutes"] >= 0
        assert rec["overtime_minutes"] >= 0
        assert rec["normal_work_minutes"] + rec["overtime_minutes"] == rec["total_work_minutes"]
    finally:
        client.delete(f"/api/v1/shifts/{sid}", headers=admin_headers)


def test_report_includes_ot_fields(client, admin_headers, employee):
    assert employee is not None
    eid = employee["id"]
    rep = client.get(f"/api/v1/reports/employee/{eid}?period=week", headers=admin_headers)
    assert rep.status_code == 200
    body = rep.json()
    assert "total_work_minutes" in body
    assert "total_normal_minutes" in body
    assert "total_overtime_minutes" in body
    for rc in body["records"]:
        assert "normal_work_minutes" in rc
        assert "overtime_minutes" in rc
        assert "shift" in rc

    summ = client.get("/api/v1/reports/summary?period=week", headers=admin_headers).json()
    assert "total_overtime_minutes" in summ
    for d in summ["department_summary"]:
        assert "total_overtime_minutes" in d


def test_report_employee_pdf_with_ot(client, admin_headers, employee):
    assert employee is not None
    r = client.get(f"/api/v1/reports/employee/{employee['id']}?period=week&format=pdf", headers=admin_headers)
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"
