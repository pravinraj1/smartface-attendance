"""Shared fixtures for the SmartFace test suite.

Tests run against the shared Supabase database (same as the app). To stay safe
on shared data, every fixture/tests creates uniquely-named records and cleans
them up in teardown even on failure.
"""
import uuid
import random

import pytest
from fastapi.testclient import TestClient

from app.main import app

ADMIN_EMAIL = "admin@smartface.com"
ADMIN_PASSWORD = "Admin123!"

VIEWER_ROLE = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13"
HR_ROLE = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12"


def _suffix():
    return uuid.uuid4().hex[:8]


@pytest.fixture(scope="session")
def db_call(client):
    """Run an async coroutine using a dedicated engine on its own event loop.

    Uses a fresh engine (not the app's shared one) so there is no cross-loop
    mismatch between the TestClient loop and a cleanup routine's loop.
    """
    def _run(coro_fn):
        import asyncio
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.core.config import settings

        async def _runner():
            engine = create_async_engine(settings.DATABASE_URL)
            Session = async_sessionmaker(engine, expire_on_commit=False)
            try:
                async with Session() as db:
                    await coro_fn(db)
            finally:
                await engine.dispose()

        asyncio.run(_runner())

    return _run


@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def admin_headers(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 200, f"admin login failed: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def department(client, admin_headers):
    name = f"TST_Dept_{_suffix()}"
    r = client.post(
        "/api/v1/departments",
        json={"name": name, "description": "pytest fixture"},
        headers=admin_headers,
    )
    if r.status_code == 400:
        yield None
        return
    assert r.status_code == 201, f"create dept failed: {r.text}"
    dept = r.json()
    yield dept
    client.delete(f"/api/v1/departments/{dept['id']}", headers=admin_headers)


@pytest.fixture()
def employee(client, admin_headers, department):
    if department is None:
        yield None
        return
    code = f"T{random.randint(10000, 99999)}"
    r = client.post(
        "/api/v1/employees",
        json={
            "employee_code": code,
            "full_name": "Pytest Employee",
            "department_id": department["id"],
            "employment_status": "ACTIVE",
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, f"create employee failed: {r.text}"
    emp = r.json()
    yield emp
    client.delete(f"/api/v1/employees/{emp['id']}", headers=admin_headers)
