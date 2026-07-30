"""Report schedule CRUD + run-now + check-due tests."""

import httpx
from .conftest import (
    SERVER_URL,
    assert_ok,
    unique_suffix,
    _track_entity,
)


def _create_schedule(
    test_admin_headers: dict, session_suffix: str = "", suffix: str = ""
) -> str:
    """Create a report schedule and return its ID."""
    suf = suffix or unique_suffix()
    name = f"Schedule-{session_suffix}-{suf}"
    resp = httpx.post(
        f"{SERVER_URL}/api/report-schedules",
        json={
            "name": name,
            "report_type": "revenue",
            "schedule_frequency": "daily",
            "recipients": ["admin@test.com"],
            "schedule_config": {"hour": 8, "minute": 0},
            "filters": {"months_back": 3},
        },
        headers=test_admin_headers,
        timeout=10,
    )
    data = assert_ok(resp)
    assert data.get("ok") is True
    # Look it up by unique name via GET
    r = httpx.get(
        f"{SERVER_URL}/api/report-schedules",
        params={"search": name},
        headers=test_admin_headers,
        timeout=10,
    )
    schedules = r.json().get("schedules", [])
    assert len(schedules) >= 1
    sid = schedules[0]["id"]
    _track_entity("report_schedule", sid)
    return sid


class TestReportScheduleCRUD:
    def test_create(self, test_admin_headers: dict, session_suffix: str):
        name = f"Weekly Revenue Report {session_suffix}-{unique_suffix()}"
        resp = httpx.post(
            f"{SERVER_URL}/api/report-schedules",
            json={
                "name": name,
                "report_type": "revenue",
                "schedule_frequency": "weekly",
                "recipients": ["manager@test.com", "admin@test.com"],
                "schedule_config": {"day_of_week": 1, "hour": 9},
                "filters": {"months_back": 6},
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_create_missing_recipients(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/report-schedules",
            json={
                "name": "Bad",
                "report_type": "revenue",
                "schedule_frequency": "daily",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 400

    def test_create_invalid_type(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/report-schedules",
            json={
                "name": "Bad",
                "report_type": "nonexistent",
                "schedule_frequency": "daily",
                "recipients": ["x@x.com"],
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 400

    def test_create_invalid_frequency(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/report-schedules",
            json={
                "name": "Bad",
                "report_type": "revenue",
                "schedule_frequency": "yearly",
                "recipients": ["x@x.com"],
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 400

    def test_list(self, test_admin_headers: dict, session_suffix: str):
        _create_schedule(test_admin_headers, session_suffix, "lst")
        resp = httpx.get(
            f"{SERVER_URL}/api/report-schedules", headers=test_admin_headers, timeout=10
        )
        data = assert_ok(resp)
        assert "schedules" in data
        assert "total" in data

    def test_update(self, test_admin_headers: dict, session_suffix: str):
        sid = _create_schedule(test_admin_headers, session_suffix, "upd")
        resp = httpx.put(
            f"{SERVER_URL}/api/report-schedules/{sid}",
            json={
                "name": "Updated Report",
                "report_type": "tickets",
                "schedule_frequency": "weekly",
                "recipients": ["updated@test.com"],
                "enabled": True,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_update_nonexistent(self, test_admin_headers: dict):
        resp = httpx.put(
            f"{SERVER_URL}/api/report-schedules/nonexistent-999",
            json={
                "name": "Nope",
                "report_type": "revenue",
                "schedule_frequency": "daily",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 404

    def test_delete(self, test_admin_headers: dict, session_suffix: str):
        sid = _create_schedule(test_admin_headers, session_suffix, "del")
        resp = httpx.delete(
            f"{SERVER_URL}/api/report-schedules/{sid}",
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_delete_nonexistent(self, test_admin_headers: dict):
        resp = httpx.delete(
            f"{SERVER_URL}/api/report-schedules/nonexistent-999",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code < 500


class TestReportScheduleRun:
    def test_run_now(self, test_admin_headers: dict, session_suffix: str):
        """Run-now should attempt delivery (may fail without mail config, that's ok)."""
        sid = _create_schedule(test_admin_headers, session_suffix, "run")
        # Need to ensure recipients includes an email to avoid validation issues
        resp = httpx.post(
            f"{SERVER_URL}/api/report-schedules/{sid}/run-now",
            headers=test_admin_headers,
            timeout=15,
        )
        # Should not crash — may fail gracefully due to no mail config
        assert resp.status_code < 500, resp.text[:200]

    def test_run_now_nonexistent(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/report-schedules/nonexistent-999/run-now",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 404

    def test_check_due(self, test_admin_headers: dict):
        """Check-due should return a list, possibly empty."""
        resp = httpx.get(
            f"{SERVER_URL}/api/report-schedules/check-due",
            headers=test_admin_headers,
            timeout=15,
        )
        data = assert_ok(resp)
        assert "processed" in data
        assert "results" in data


class TestReportScheduleErrors:
    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/report-schedules", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post(
            "/api/report-schedules",
            json={
                "name": "X",
                "report_type": "revenue",
                "schedule_frequency": "daily",
                "recipients": ["x@x.com"],
            },
            timeout=10,
        )
        assert resp.status_code in (401, 403)
