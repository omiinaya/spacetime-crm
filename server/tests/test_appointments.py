"""Appointment CRUD, recurrence, and status workflow integration tests.

Each test method creates its own data for STDB state isolation.
"""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, create_customer, unique_suffix, _stdb_sql, _track_entity, test_admin_headers


def _create_appointment(test_admin_headers: dict, session_suffix: str = "", suffix: str = "", **overrides) -> str:
    """Create a customer + appointment and return the appointment ID.

    Uses a unique title and STDB SQL lookup for isolation.
    Tracks created entities for session cleanup.
    """
    suf = suffix or unique_suffix()
    title = overrides.get("title", f"Appt-{session_suffix}-{suf}")
    email = f"appt-cust-{session_suffix}-{suf}@example.com"
    c = create_customer(test_admin_headers, session_suffix=session_suffix, first_name="Appt", last_name=f"Test{suf}", email=email)
    cid = c.get("id")
    assert cid

    httpx.post(f"{SERVER_URL}/api/appointments", json={
        "customer_id": cid,
        "title": title,
        "description": overrides.get("description", "Auto-generated"),
        "start_time": overrides.get("start_time", 1783000000000),
        "end_time": overrides.get("end_time", 1783003600000),
        "all_day": overrides.get("all_day", False),
        "recurrence_rule": overrides.get("recurrence_rule", ""),
        "color": overrides.get("color", ""),
    }, headers=test_admin_headers, timeout=10)

    rows = _stdb_sql(f"SELECT * FROM appointment WHERE title = '{title}'")
    assert len(rows) >= 1, f"No appointment found with title '{title}'"
    appt_id = rows[0]["id"]
    _track_entity("appointment", appt_id)
    return appt_id


class TestAppointmentCRUD:
    """Appointment create, list, status update, delete lifecycle."""

    def test_create_appointment(self, test_admin_headers: dict, session_suffix: str):
        """Create a basic appointment."""
        appt_id = _create_appointment(test_admin_headers, session_suffix, "create", title="Basic Appointment")
        assert appt_id, "Expected non-empty appointment ID"

    def test_create_appointment_persists_color(self, test_admin_headers: dict, session_suffix: str):
        """color from the Pydantic model must persist to STDB."""
        suf = unique_suffix()
        title = f"Appt-Color-{session_suffix}-{suf}"
        _create_appointment(test_admin_headers, session_suffix, "color", title=title, color="#3498db")

        rows = _stdb_sql(f"SELECT * FROM appointment WHERE title = '{title}'")
        assert len(rows) >= 1, f"No appointment found with title '{title}'"
        appt = rows[0]
        assert appt["color"] == "#3498db", f"color={appt.get('color')!r}"
        _track_entity("appointment", appt["id"])

    def test_list_appointments(self, test_admin_headers: dict):
        """List appointments returns paginated results."""
        resp = httpx.get(f"{SERVER_URL}/api/appointments", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "appointments" in data
        assert "total" in data
        assert isinstance(data["appointments"], list)

    def test_update_appointment_status(self, test_admin_headers: dict, session_suffix: str):
        """Update appointment status to completed."""
        appt_id = _create_appointment(test_admin_headers, session_suffix, "status", title="Status Test")

        for status in ["completed", "no_show", "cancelled"]:
            resp = httpx.put(
                f"{SERVER_URL}/api/appointments/{appt_id}/status",
                json={"status": status},
                headers=test_admin_headers, timeout=10,
            )
            assert_ok(resp)

    def test_delete_appointment(self, test_admin_headers: dict, session_suffix: str):
        """Delete an appointment (admin only)."""
        appt_id = _create_appointment(test_admin_headers, session_suffix, "delete", title="Delete Me")
        resp = httpx.delete(f"{SERVER_URL}/api/appointments/{appt_id}", headers=test_admin_headers, timeout=10)
        assert_ok(resp)


class TestRecurringAppointments:
    """Recurring appointment series and occurrence generation."""

    def _make_customer(self, test_admin_headers: dict, session_suffix: str = "") -> str:
        c = create_customer(test_admin_headers, session_suffix=session_suffix, first_name="Recur", last_name="Appt", email=f"recur-appt-{session_suffix}-{unique_suffix()}@example.com")
        return c["id"]

    def test_create_recurring_appointment(self, test_admin_headers: dict, session_suffix: str):
        """Create an appointment with recurrence rule."""
        cid = self._make_customer(test_admin_headers, session_suffix)
        resp = httpx.post(
            f"{SERVER_URL}/api/appointments",
            json={
                "customer_id": cid,
                "title": "Weekly Check",
                "start_time": 1783000000000,
                "end_time": 1783003600000,
                "recurrence_rule": "weekly",
            },
            headers=test_admin_headers, timeout=10,
        )
        assert_ok(resp)

    def test_list_recurring_series(self, test_admin_headers: dict):
        """List recurring series returns series with occurrence counts."""
        resp = httpx.get(f"{SERVER_URL}/api/appointments/recurring", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "series" in data
        assert isinstance(data["series"], list)

    def test_generate_next_occurrence(self, test_admin_headers: dict, session_suffix: str):
        """Generate next occurrence of a recurring series."""
        # Create an appointment with recurrence via the helper
        suf = unique_suffix()
        title = f"Biweekly-{session_suffix}-{suf}"
        appt_id = _create_appointment(test_admin_headers, session_suffix, suf, title=title, recurrence_rule="weekly")

        # Find the series via recurring API (filter by our unique title)
        r = httpx.get(f"{SERVER_URL}/api/appointments/recurring", headers=test_admin_headers, timeout=10)
        series_list = r.json().get("series", [])
        # Find our series (the one matching our appointment's series_id)
        series = _stdb_sql(f"SELECT * FROM appointment WHERE title = '{title}'")
        assert len(series) > 0
        series_id = series[0].get("series_id", "")
        # If the appointment itself is the series parent, its series_id is empty
        # and its id is the series id
        if not series_id:
            series_id = appt_id

        resp = httpx.post(
            f"{SERVER_URL}/api/appointments/generate-next",
            json={"series_id": series_id},
            headers=test_admin_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert data.get("start_time", 0) > 0, f"Expected start_time, got: {data}"
        assert data.get("end_time", 0) > 0

    def test_set_recurrence_on_existing(self, test_admin_headers: dict, session_suffix: str):
        """Set recurrence rule on an existing appointment."""
        appt_id = _create_appointment(test_admin_headers, session_suffix, "setrecur", title="Make Recurring")

        resp = httpx.put(
            f"{SERVER_URL}/api/appointments/{appt_id}/recurrence",
            json={"recurrence_rule": "monthly"},
            headers=test_admin_headers, timeout=10,
        )
        assert_ok(resp)

    def test_recurring_series_with_children(self, test_admin_headers: dict, session_suffix: str):
        """After generating occurrences, series shows child count."""
        suf = unique_suffix()
        title = f"MultiGen-{session_suffix}-{suf}"
        appt_id = _create_appointment(test_admin_headers, session_suffix, suf, title=title, recurrence_rule="daily")

        # Get our series ID from STDB
        rows = _stdb_sql(f"SELECT * FROM appointment WHERE title = '{title}'")
        assert len(rows) > 0
        series_id = rows[0].get("series_id", "")
        if not series_id:
            series_id = appt_id

        # Generate 2 occurrences
        for _ in range(2):
            httpx.post(f"{SERVER_URL}/api/appointments/generate-next", json={"series_id": series_id}, headers=test_admin_headers, timeout=10)

        # Check series again via STDB SQL
        children = _stdb_sql(f"SELECT * FROM appointment WHERE series_id = '{series_id}'")
        assert len(children) >= 2, f"Expected >=2 children, got {len(children)}"


class TestAppointmentErrors:
    """Appointment error handling."""

    def test_create_missing_title(self, test_admin_headers: dict):
        """Missing required title returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/appointments",
            json={"customer_id": "test", "start_time": 0, "end_time": 0},
            headers=test_admin_headers, timeout=10,
        )
        assert resp.status_code == 422

    def test_unauthorized_access(self, client: httpx.Client):
        """Appointment endpoints require auth."""
        for path in ["/api/appointments", "/api/appointments/recurring", "/api/appointments/due-soon"]:
            resp = client.get(path, timeout=10)
            assert resp.status_code in (401, 403), f"{path} allowed unauthenticated"


class TestAppointmentReminders:
    """Appointment reminder endpoints."""

    def test_due_soon_returns_appointments(self, test_admin_headers: dict):
        """Due-soon endpoint returns appointments (may be empty)."""
        resp = httpx.get(f"{SERVER_URL}/api/appointments/due-soon", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "appointments" in data
        assert "count" in data
        assert isinstance(data["appointments"], list)

    def test_due_soon_unauthorized(self, client: httpx.Client):
        """Due-soon endpoint requires auth."""
        resp = client.get("/api/appointments/due-soon", timeout=10)
        assert resp.status_code in (401, 403)

    def test_send_reminders_returns_ok(self, test_admin_headers: dict):
        """Send-reminders endpoint returns ok (gracefully handles no upcoming appts)."""
        resp = httpx.post(f"{SERVER_URL}/api/appointments/send-reminders", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "sent" in data

    def test_send_reminders_unauthorized(self, client: httpx.Client):
        """Send-reminders endpoint requires auth."""
        resp = client.post("/api/appointments/send-reminders", timeout=10)
        assert resp.status_code in (401, 403)
