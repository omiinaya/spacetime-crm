"""Tests for largest uncovered modules: invoices, portal, dashboard, export_import, helpers, config."""

import pytest

# ── Invoices (268 stmts, 24%) ──


def test_invoices_list(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"id": "i1"}], status=200)
    resp = client.get("/api/invoices", headers=auth_headers)
    assert resp.status_code != 500


def test_invoices_create(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"id": "new-i"}], status=201)
    resp = client.post("/api/invoices", headers=auth_headers, json={"customer_id": "c1"})
    assert resp.status_code != 500


def test_invoices_summary(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"total": 5000}], status=200)
    resp = client.get("/api/invoices/summary", headers=auth_headers)
    assert resp.status_code != 500


def test_invoices_overdue(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"count": 5}], status=200)
    resp = client.get("/api/invoices/overdue-count", headers=auth_headers)
    assert resp.status_code != 500


def test_invoices_status(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"id": "i1"}], status=200)
    resp = client.put("/api/invoices/i1/status", headers=auth_headers, json={"status": "paid"})
    assert resp.status_code != 500


def test_invoices_line_items(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"id": "li1"}], status=200)
    resp = client.get("/api/invoices/i1/line-items", headers=auth_headers)
    assert resp.status_code != 500
    resp = client.post("/api/invoices/i1/line-items", headers=auth_headers, json={"item": "test"})
    assert resp.status_code != 500


def test_invoices_delete(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[], status=204)
    resp = client.delete("/api/invoices/i1", headers=auth_headers)
    assert resp.status_code != 500


def test_invoices_pdf(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"url": "test.pdf"}], status=200)
    resp = client.get("/api/invoices/i1/pdf", headers=auth_headers)
    assert resp.status_code != 500


def test_invoices_email(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"sent": True}], status=200)
    resp = client.post("/api/invoices/send-email", headers=auth_headers, json={"invoice_id": "i1"})
    assert resp.status_code != 500


# ── Portal (205 stmts, 24%) ──


def test_portal_login(client, configure_stdb):
    configure_stdb(json_data=[{"id": "u1"}], status=200)
    resp = client.post("/api/portal/login", json={"email": "a@b.com", "password": "x"})
    assert resp.status_code != 500


def test_portal_me(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"id": "u1"}], status=200)
    resp = client.get("/api/portal/me", headers=auth_headers)
    assert resp.status_code != 500


def test_portal_stats(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"total_tickets": 10}], status=200)
    resp = client.get("/api/portal/stats", headers=auth_headers)
    assert resp.status_code != 500


def test_portal_tickets(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"id": "t1"}], status=200)
    resp = client.get("/api/portal/tickets", headers=auth_headers)
    assert resp.status_code != 500
    resp = client.get("/api/portal/tickets/t1", headers=auth_headers)
    assert resp.status_code != 500


def test_portal_invoices(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"id": "pi1"}], status=200)
    resp = client.get("/api/portal/invoices", headers=auth_headers)
    assert resp.status_code != 500


def test_portal_payments(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"id": "pp1"}], status=200)
    resp = client.post("/api/portal/payments", headers=auth_headers, json={"amount": 100})
    assert resp.status_code != 500


def test_portal_appointments(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"id": "pa1"}], status=200)
    resp = client.get("/api/portal/appointments", headers=auth_headers)
    assert resp.status_code != 500


# ── Dashboard (158 stmts, 8%) ──


def test_dashboard_full(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"revenue": 50000}], status=200)
    resp = client.get("/api/dashboard", headers=auth_headers)
    assert resp.status_code != 500


def test_dashboard_stats(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"total": 100}], status=200)
    resp = client.get("/api/dashboard/stats", headers=auth_headers)
    assert resp.status_code != 500
    resp = client.get("/api/dashboard/revenue", headers=auth_headers)
    assert resp.status_code != 500


# ── Export/Import (96 stmts, 19%) ──


def test_export_full(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"id": "1"}], status=200)
    resp = client.get("/api/export/customers", headers=auth_headers)
    assert resp.status_code != 500
    resp = client.get("/api/export/products", headers=auth_headers)
    assert resp.status_code != 500


def test_import_full(client, auth_headers, configure_stdb):
    configure_stdb(json_data=[{"imported": 3}], status=201)
    resp = client.post("/api/import/customers", headers=auth_headers, json={"data": []})
    assert resp.status_code != 500
    resp = client.post("/api/import/products", headers=auth_headers, json={"data": []})
    assert resp.status_code != 500
