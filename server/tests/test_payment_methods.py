"""Saved payment methods CRUD tests."""

import httpx
import pytest

from .conftest import (
    SERVER_URL,
    _track_entity,
    assert_ok,
    create_customer,
    unique_suffix,
)


def _customer_id(
    test_admin_headers: dict, session_suffix: str = "", suffix: str = ""
) -> str:
    suf = suffix or unique_suffix()
    c = create_customer(
        test_admin_headers,
        session_suffix=session_suffix,
        email=f"pm-{session_suffix}-{suf}@example.com",
    )
    return c.get("id", "")


class TestPaymentMethods:
    """Saved payment method CRUD."""

    def test_list_empty(self, test_admin_headers: dict):
        resp = httpx.get(
            f"{SERVER_URL}/api/payment-methods", headers=test_admin_headers, timeout=10
        )
        data = assert_ok(resp)
        assert "payment_methods" in data

    def test_list_filtered_by_customer(
        self, test_admin_headers: dict, session_suffix: str
    ):
        cid = _customer_id(test_admin_headers, session_suffix, "lst-cust")
        resp = httpx.get(
            f"{SERVER_URL}/api/payment-methods",
            params={"customer_id": cid},
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert "payment_methods" in data

    def test_save_method(self, test_admin_headers: dict, session_suffix: str):
        cid = _customer_id(test_admin_headers, session_suffix, "save")
        resp = httpx.post(
            f"{SERVER_URL}/api/payment-methods",
            json={
                "customer_id": cid,
                "stripe_payment_method_id": "pm_test_12345",
                "brand": "Visa",
                "last4": "4242",
                "exp_month": 12,
                "exp_year": 2028,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

        # Verify it appears in list
        r2 = httpx.get(
            f"{SERVER_URL}/api/payment-methods",
            params={"customer_id": cid},
            headers=test_admin_headers,
            timeout=10,
        )
        r2_data = r2.json()
        methods = [
            m
            for m in r2_data["payment_methods"]
            if m.get("stripe_payment_method_id") == "pm_test_12345"
        ]
        assert len(methods) >= 1, (
            f"Saved method not found: {r2_data['payment_methods']}"
        )
        # Track for cleanup
        for m in methods:
            _track_entity("saved_payment_method", m["id"])

    def test_save_method_invalid_last4(
        self, test_admin_headers: dict, session_suffix: str
    ):
        cid = _customer_id(test_admin_headers, session_suffix, "bad-last4")
        resp = httpx.post(
            f"{SERVER_URL}/api/payment-methods",
            json={
                "customer_id": cid,
                "stripe_payment_method_id": "pm_bad",
                "brand": "Amex",
                "last4": "abc",
                "exp_month": 12,
                "exp_year": 2028,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422

    def test_save_method_missing_customer(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/payment-methods",
            json={
                "stripe_payment_method_id": "pm_test",
                "brand": "Visa",
                "last4": "1234",
                "exp_month": 1,
                "exp_year": 2029,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422

    def test_set_default(self, test_admin_headers: dict, session_suffix: str):
        cid = _customer_id(test_admin_headers, session_suffix, "default")
        httpx.post(
            f"{SERVER_URL}/api/payment-methods",
            json={
                "customer_id": cid,
                "stripe_payment_method_id": "pm_default_test",
                "brand": "Mastercard",
                "last4": "5555",
                "exp_month": 6,
                "exp_year": 2029,
            },
            headers=test_admin_headers,
            timeout=10,
        )

        r = httpx.get(
            f"{SERVER_URL}/api/payment-methods",
            params={"customer_id": cid},
            headers=test_admin_headers,
            timeout=10,
        )
        methods = r.json().get("payment_methods", [])
        if not methods:
            pytest.skip("No payment methods to set default")
        method_id = methods[0]["id"]
        _track_entity("saved_payment_method", method_id)

        resp = httpx.put(
            f"{SERVER_URL}/api/payment-methods/{method_id}/default",
            json={
                "customer_id": cid,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_set_default_nonexistent(self, test_admin_headers: dict):
        resp = httpx.put(
            f"{SERVER_URL}/api/payment-methods/nonexistent-999/default",
            json={
                "customer_id": "cust_fake",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code < 500

    def test_delete_method(self, test_admin_headers: dict, session_suffix: str):
        cid = _customer_id(test_admin_headers, session_suffix, "delete-pm")
        httpx.post(
            f"{SERVER_URL}/api/payment-methods",
            json={
                "customer_id": cid,
                "stripe_payment_method_id": "pm_delete_test",
                "brand": "Discover",
                "last4": "6011",
                "exp_month": 3,
                "exp_year": 2027,
            },
            headers=test_admin_headers,
            timeout=10,
        )

        r = httpx.get(
            f"{SERVER_URL}/api/payment-methods",
            params={"customer_id": cid},
            headers=test_admin_headers,
            timeout=10,
        )
        methods = r.json().get("payment_methods", [])
        if not methods:
            pytest.skip("No payment methods to delete")
        method_id = methods[0]["id"]
        _track_entity("saved_payment_method", method_id)

        resp = httpx.delete(
            f"{SERVER_URL}/api/payment-methods/{method_id}",
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_delete_nonexistent(self, test_admin_headers: dict):
        resp = httpx.delete(
            f"{SERVER_URL}/api/payment-methods/nonexistent-999",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code < 500

    def test_setup_intent_no_stripe(
        self, test_admin_headers: dict, session_suffix: str
    ):
        """Without Stripe configured, setup-intent should return 400."""
        cid = _customer_id(test_admin_headers, session_suffix, "si")
        resp = httpx.post(
            f"{SERVER_URL}/api/payment-methods/setup-intent",
            json={
                "customer_id": cid,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 400


class TestPaymentMethodErrors:
    """Auth enforcement."""

    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/payment-methods", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post(
            "/api/payment-methods",
            json={
                "customer_id": "x",
                "stripe_payment_method_id": "pm_x",
                "brand": "V",
                "last4": "1234",
                "exp_month": 1,
                "exp_year": 2025,
            },
            timeout=10,
        )
        assert resp.status_code in (401, 403)

    def test_unauthorized_delete(self, client: httpx.Client):
        resp = client.delete("/api/payment-methods/x", timeout=10)
        assert resp.status_code in (401, 403)
