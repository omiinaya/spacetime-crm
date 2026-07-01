"""Appointment CRUD, recurrence, and status workflow integration tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, create_customer


class TestAppointmentCRUD:
    """Appointment create, list, status update, delete lifecycle."""

    def _make_customer(self, auth_headers: dict, suffix: str = "") -> str:
        email = f"appt-cust-{suffix or 'main'}@example.com"
        c = create_customer(auth_headers, first_name="Appt", last_name=f"Test{suffix}", email=email)
        cid = c.get("id")
        assert cid
        return cid

    def test_create_appointment(self, auth_headers: dict):
        """Create a basic appointment."""
        cid = self._make_customer(auth_headers, "create")
        resp = httpx.post(
            f"{SERVER_URL}/api/appointments",
            json={
                "customer_id": cid,
                "title": "Test Appointment",
                "description": "Annual checkup",
                "start_time": 1783000000000,
                "end_time": 1783003600000,
                "all_day": False,
            },
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_list_appointments(self, auth_headers: dict):
        """List appointments returns paginated results."""
        resp = httpx.get(f"{SERVER_URL}/api/appointments", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "appointments" in data
        assert "total" in data
        assert isinstance(data["appointments"], list)

    def test_update_appointment_status(self, auth_headers: dict):
        """Update appointment status to completed."""
        cid = self._make_customer(auth_headers, "status")
        httpx.post(f"{SERVER_URL}/api/appointments", json={"customer_id": cid, "title": "Status Test", "start_time": 1783000000000, "end_time": 1783003600000}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/appointments", params={"limit": 1}, headers=auth_headers, timeout=10)
        appts = r.json().get("appointments", [])
        if not appts:
            pytest.skip("No appointments found")
        appt_id = appts[0]["id"]

        for status in ["completed", "no_show", "cancelled"]:
            resp = httpx.put(
                f"{SERVER_URL}/api/appointments/{appt_id}/status",
                json={"status": status},
                headers=auth_headers, timeout=10,
            )
            assert_ok(resp)

    def test_delete_appointment(self, auth_headers: dict):
        """Delete an appointment (admin only)."""
        cid = self._make_customer(auth_headers, "delete")
        httpx.post(f"{SERVER_URL}/api/appointments", json={"customer_id": cid, "title": "Delete Me", "start_time": 1783000000000, "end_time": 1783003600000}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/appointments", params={"limit": 1}, headers=auth_headers, timeout=10)
        appts = r.json().get("appointments", [])
        if not appts:
            pytest.skip("No appointments found")
        appt_id = appts[0]["id"]

        resp = httpx.delete(f"{SERVER_URL}/api/appointments/{appt_id}", headers=auth_headers, timeout=10)
        assert_ok(resp)


class TestRecurringAppointments:
    """Recurring appointment series and occurrence generation."""

    def _make_customer(self, auth_headers: dict) -> str:
        c = create_customer(auth_headers, first_name="Recur", last_name="Appt", email="recur-appt@example.com")
        return c["id"]

    def test_create_recurring_appointment(self, auth_headers: dict):
        """Create an appointment with recurrence rule."""
        cid = self._make_customer(auth_headers)
        resp = httpx.post(
            f"{SERVER_URL}/api/appointments",
            json={
                "customer_id": cid,
                "title": "Weekly Check",
                "start_time": 1783000000000,
                "end_time": 1783003600000,
                "recurrence_rule": "weekly",
            },
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_list_recurring_series(self, auth_headers: dict):
        """List recurring series returns series with occurrence counts."""
        resp = httpx.get(f"{SERVER_URL}/api/appointments/recurring", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "series" in data
        assert isinstance(data["series"], list)

    def test_generate_next_occurrence(self, auth_headers: dict):
        """Generate next occurrence of a recurring series."""
        cid = self._make_customer(auth_headers)
        httpx.post(f"{SERVER_URL}/api/appointments", json={"customer_id": cid, "title": "Biweekly", "start_time": 1783000000000, "end_time": 1783003600000, "recurrence_rule": "weekly"}, headers=auth_headers, timeout=10)

        r = httpx.get(f"{SERVER_URL}/api/appointments/recurring", headers=auth_headers, timeout=10)
        series = r.json().get("series", [])
        if not series:
            pytest.skip("No recurring series found")

        series_id = series[0]["id"]
        resp = httpx.post(
            f"{SERVER_URL}/api/appointments/generate-next",
            json={"series_id": series_id},
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert data.get("start_time", 0) > 0, f"Expected start_time, got: {data}"
        assert data.get("end_time", 0) > 0

    def test_set_recurrence_on_existing(self, auth_headers: dict):
        """Set recurrence rule on an existing appointment."""
        cid = self._make_customer(auth_headers)
        httpx.post(f"{SERVER_URL}/api/appointments", json={"customer_id": cid, "title": "Make Recurring", "start_time": 1783000000000, "end_time": 1783003600000}, headers=auth_headers, timeout=10)
        r = httpx.get(f"{SERVER_URL}/api/appointments", params={"limit": 1}, headers=auth_headers, timeout=10)
        appts = r.json().get("appointments", [])
        if not appts:
            pytest.skip("No appointments found")
        appt_id = appts[0]["id"]

        resp = httpx.put(
            f"{SERVER_URL}/api/appointments/{appt_id}/recurrence",
            json={"recurrence_rule": "monthly"},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_recurring_series_with_children(self, auth_headers: dict):
        """After generating occurrences, series shows child count."""
        cid = self._make_customer(auth_headers)
        httpx.post(f"{SERVER_URL}/api/appointments", json={"customer_id": cid, "title": "Multi Gen", "start_time": 1783000000000, "end_time": 1783003600000, "recurrence_rule": "daily"}, headers=auth_headers, timeout=10)

        r = httpx.get(f"{SERVER_URL}/api/appointments/recurring", headers=auth_headers, timeout=10)
        series = r.json().get("series", [])
        if not series:
            pytest.skip("No recurring series")
        sid = series[0]["id"]

        # Generate 2 occurrences
        for _ in range(2):
            httpx.post(f"{SERVER_URL}/api/appointments/generate-next", json={"series_id": sid}, headers=auth_headers, timeout=10)

        # Check series again
        r2 = httpx.get(f"{SERVER_URL}/api/appointments/recurring", headers=auth_headers, timeout=10)
        for s in r2.json().get("series", []):
            if s["id"] == sid:
                assert s.get("occurrence_count", 0) >= 2, f"Expected >=2 children, got {s.get('occurrence_count')}"
                break


class TestAppointmentErrors:
    """Appointment error handling."""

    def test_create_missing_title(self, auth_headers: dict):
        """Missing required title returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/appointments",
            json={"customer_id": "test", "start_time": 0, "end_time": 0},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 422

    def test_unauthorized_access(self, client: httpx.Client):
        """Appointment endpoints require auth."""
        for path in ["/api/appointments", "/api/appointments/recurring", "/api/appointments/due-soon"]:
            resp = client.get(path, timeout=10)
            assert resp.status_code in (401, 403), f"{path} allowed unauthenticated"


class TestAppointmentReminders:
    """Appointment reminder endpoints."""

    def test_due_soon_returns_appointments(self, auth_headers: dict):
        """Due-soon endpoint returns appointments (may be empty)."""
        resp = httpx.get(f"{SERVER_URL}/api/appointments/due-soon", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "appointments" in data
        assert "count" in data
        assert isinstance(data["appointments"], list)

    def test_due_soon_unauthorized(self, client: httpx.Client):
        """Due-soon endpoint requires auth."""
        resp = client.get("/api/appointments/due-soon", timeout=10)
        assert resp.status_code in (401, 403)

    def test_send_reminders_returns_ok(self, auth_headers: dict):
        """Send-reminders endpoint returns ok (gracefully handles no upcoming appts)."""
        resp = httpx.post(f"{SERVER_URL}/api/appointments/send-reminders", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "sent" in data

    def test_send_reminders_unauthorized(self, client: httpx.Client):
        """Send-reminders endpoint requires auth."""
        resp = client.post("/api/appointments/send-reminders", timeout=10)
        assert resp.status_code in (401, 403)
