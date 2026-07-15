"""Unit tests for invoice_delivery module (extracted from routes/invoices.py)."""

from unittest.mock import MagicMock
import pytest
from invoice_delivery import (
    INVOICE_STATUSES,
    STATUS_CSS,
    STATUS_LABELS,
    build_invoice_data,
    get_due_invoices,
    send_invoice_notification,
    send_batch_notifications,
)


class TestInvoiceStatusUtils:
    def test_status_css_contains_key_statuses(self):
        assert "draft" in STATUS_CSS
        assert "sent" in STATUS_CSS
        assert "paid" in STATUS_CSS
        assert "overdue" in STATUS_CSS
        assert "cancelled" in STATUS_CSS

    def test_status_labels_contains_all(self):
        assert STATUS_LABELS["draft"] == "Draft"
        assert STATUS_LABELS["sent"] == "Sent"
        assert STATUS_LABELS["paid"] == "Paid"
        assert STATUS_LABELS["overdue"] == "Overdue"

    def test_invoice_statuses_contains_all_statuses(self):
        assert "draft" in INVOICE_STATUSES
        assert "sent" in INVOICE_STATUSES
        assert "paid" in INVOICE_STATUSES
        assert "overdue" in INVOICE_STATUSES
        assert len(INVOICE_STATUSES) >= 6


class TestBuildInvoiceData:
    def test_build_invoice_data_with_all_fields(self):
        inv = {
            "id": "inv1",
            "invoice_number": "INV-001",
            "total": "250.00",
            "status": "sent",
            "customer_id": "c1",
            "due_date": 1700000000000,
            "created_at": 1690000000000,
            "currency": "USD",
        }
        data = build_invoice_data(inv)
        assert data["id"] == "inv1"
        assert data["number"] == "INV-001"
        assert data["total"] == 250.00
        assert data["status"] == "sent"
        assert data["customer_id"] == "c1"

    def test_build_invoice_data_minimal(self):
        inv = {"id": "inv2", "total": "100"}
        data = build_invoice_data(inv)
        assert data["total"] == 100.0
        assert data["status"] == "unknown"

    def test_build_invoice_data_float_total(self):
        inv = {"id": "inv3", "total": 99.99, "status": "paid"}
        data = build_invoice_data(inv)
        assert data["total"] == 99.99
        assert data["status"] == "paid"


class TestGetDueInvoices:
    def test_get_due_invoices_filters_correctly(self):
        now = 1710000000000
        invoices = [
            {"id": "inv1", "status": "sent", "due_date": 1700000000000},
            {"id": "inv2", "status": "paid", "due_date": 1690000000000},
            {"id": "inv3", "status": "sent", "due_date": 1720000000000},
            {"id": "inv4", "status": "partial", "due_date": 1705000000000},
        ]
        due = get_due_invoices(invoices, now)
        assert len(due) == 2
        assert due[0]["id"] == "inv1"
        assert due[1]["id"] == "inv4"

    def test_get_due_invoices_empty(self):
        assert get_due_invoices([], 1710000000000) == []


class TestSendInvoiceNotification:
    @pytest.mark.asyncio
    async def test_send_notification_sends_email(self):
        mock_send = MagicMock()
        result = await send_invoice_notification(
            email="cust@example.com",
            phone="",
            invoice_number="INV-001",
            total=100.0,
            portal_link="https://app.example.com/portal/",
            send_email_func=mock_send,
        )
        assert result["email"] is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_sends_sms(self):
        mock_send_sms = MagicMock()
        result = await send_invoice_notification(
            email="",
            phone="+1234567890",
            invoice_number="INV-002",
            total=200.0,
            portal_link="https://app.example.com/portal/",
            send_email_func=None,
            send_sms_func=mock_send_sms,
        )
        assert result["sms"] is True
        mock_send_sms.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_no_contact(self):
        result = await send_invoice_notification(
            email="",
            phone="",
            invoice_number="INV-003",
            total=50.0,
        )
        assert result["email"] is False
        assert result["sms"] is False


class TestSendBatchNotifications:
    @pytest.mark.asyncio
    async def test_batch_empty_list(self):
        result = await send_batch_notifications(invoices=[])
        assert result["sent"] == 0
        assert result["failed"] == 0
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_batch_sends_to_valid_invoices(self):
        invoices_data = [
            {"id": "inv1", "invoice_number": "001", "total": "100", "customer_email": "a@b.com", "customer_phone": ""},
            {"id": "inv2", "invoice_number": "002", "total": "200", "customer_email": "c@d.com", "customer_phone": ""},
        ]
        result = await send_batch_notifications(
            invoices=invoices_data,
            send_email_func=lambda e, n, t, l: None,
        )
        assert result["sent"] == 2
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_batch_skips_no_email(self):
        invoices_data = [
            {"id": "inv1", "invoice_number": "001", "total": "100", "customer_email": None, "customer_phone": ""},
        ]
        result = await send_batch_notifications(invoices=invoices_data)
        assert result["skipped"] == 1
        assert result["sent"] == 0
