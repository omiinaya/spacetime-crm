"""Unit tests for report_schedules routes."""

from unittest.mock import AsyncMock

import jwt

from config import settings


def make_token(user_id="user-1", role="admin", tenant_id="t1"):
    return jwt.encode(
        {"sub": user_id, "tenant_id": tenant_id, "role": role},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def auth_headers(role="admin"):
    return {"Authorization": f"Bearer {make_token(role=role)}"}


class TestReportSchedules:
    def test_list_schedules(self, client, monkeypatch) -> None:
        """GET /api/report-schedules returns schedules list."""
        schedules = [
            {"id": "s1", "name": "Daily Report", "next_run_at": 1000},
            {"id": "s2", "name": "Weekly Report", "next_run_at": 2000},
        ]
        mock_sql_t = AsyncMock(return_value=schedules)
        monkeypatch.setattr("routes.report_schedules._sql_t", mock_sql_t)

        resp = client.get("/api/report-schedules", headers=auth_headers())
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "schedules" in data
        assert len(data["schedules"]) == 2
        assert data["total"] == 2

    def test_create_schedule(self, client, monkeypatch) -> None:
        """POST /api/report-schedules creates a schedule."""
        mock_call = AsyncMock(return_value={"id": "sched-1"})
        monkeypatch.setattr("routes.report_schedules._call", mock_call)

        body = {
            "name": "Test Schedule",
            "report_type": "revenue",
            "schedule_frequency": "daily",
            "schedule_config": {"time": "08:00"},
            "recipients": ["admin@example.com"],
            "filters": {},
        }
        resp = client.post("/api/report-schedules", json=body, headers=auth_headers())
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["ok"] is True
        assert data["id"] == "sched-1"

    def test_delete_schedule(self, client, monkeypatch) -> None:
        """DELETE /api/report-schedules/{id} deletes a schedule."""
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.report_schedules._call", mock_call)

        resp = client.delete("/api/report-schedules/sched-1", headers=auth_headers())
        assert resp.status_code == 200, resp.text

    def test_update_schedule(self, client, monkeypatch) -> None:
        """PUT /api/report-schedules/{id} updates a schedule."""
        mock_sql = AsyncMock(return_value=[{"id": "sched-1"}])
        mock_call = AsyncMock(return_value={"id": "sched-1"})
        monkeypatch.setattr("routes.report_schedules._sql", mock_sql)
        monkeypatch.setattr("routes.report_schedules._call", mock_call)

        resp = client.put(
            "/api/report-schedules/sched-1",
            json={
                "name": "Updated",
                "report_type": "revenue",
                "schedule_frequency": "daily",
                "recipients": ["a@b.com"],
            },
            headers=auth_headers(),
        )
        assert resp.status_code == 200, resp.text

    def test_update_schedule_not_found(self, client, monkeypatch) -> None:
        """PUT with non-existent id returns 404."""
        mock_sql = AsyncMock(return_value=[])
        monkeypatch.setattr("routes.report_schedules._sql", mock_sql)

        resp = client.put(
            "/api/report-schedules/nonexistent",
            json={
                "name": "Updated",
                "report_type": "revenue",
                "schedule_frequency": "daily",
                "recipients": ["a@b.com"],
            },
            headers=auth_headers(),
        )
        assert resp.status_code == 404, resp.text
