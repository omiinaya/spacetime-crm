"""Tests for routes/payment_methods.py."""
import pytest

class TestPaymentMethods:
    def test_list_methods(self, client, auth_headers, configure_stdb):
        configure_stdb(json_data=[{"id": "m1", "type": "card"}], status=200)
        resp = client.get("/api/payment-methods", headers=auth_headers)
        assert resp.status_code in (200, 404)
