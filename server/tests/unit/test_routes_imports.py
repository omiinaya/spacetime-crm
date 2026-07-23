"""Basic import tests for all server route modules.

Verifies each route module can be imported without errors and exports
the expected router object.
"""
from __future__ import annotations


class TestRouteImports:
    """Each route module imports cleanly."""

    def test_health(self) -> None:
        from routes.health import router

        assert router is not None

    def test_auth(self) -> None:
        from routes.auth import router

        assert router is not None

    def test_customers(self) -> None:
        from routes.customers import router

        assert router is not None

    def test_tickets(self) -> None:
        from routes.tickets import router

        assert router is not None

    def test_invoices(self) -> None:
        from routes.invoices import router

        assert router is not None

    def test_payments(self) -> None:
        from routes.payments import router

        assert router is not None

    def test_products(self) -> None:
        from routes.products import router

        assert router is not None

    def test_appointments(self) -> None:
        from routes.appointments import router

        assert router is not None

    def test_estimates(self) -> None:
        from routes.estimates import router

        assert router is not None

    def test_purchase_orders(self) -> None:
        from routes.purchase_orders import router

        assert router is not None

    def test_settings(self) -> None:
        from routes.settings import router

        assert router is not None

    def test_users(self) -> None:
        from routes.users import router

        assert router is not None

    def test_checklists(self) -> None:
        from routes.checklists import router

        assert router is not None

    def test_custom_fields(self) -> None:
        from routes.custom_fields import router

        assert router is not None

    def test_dashboard(self) -> None:
        from routes.dashboard import router

        assert router is not None

    def test_export_import(self) -> None:
        from routes.export_import import router

        assert router is not None

    def test_payment_methods(self) -> None:
        from routes.payment_methods import router

        assert router is not None

    def test_portal(self) -> None:
        from routes.portal import router

        assert router is not None

    def test_pos(self) -> None:
        from routes.pos import router

        assert router is not None

    def test_recurring_invoices(self) -> None:
        from routes.recurring_invoices import router

        assert router is not None

    def test_report_schedules(self) -> None:
        from routes.report_schedules import router

        assert router is not None

    def test_tax_rates(self) -> None:
        from routes.tax_rates import router

        assert router is not None

    def test_tenants(self) -> None:
        from routes.tenants import router

        assert router is not None

    def test_webhooks(self) -> None:
        from routes.webhooks import router

        assert router is not None

    def test_routes_init(self) -> None:
        from routes import register_routers

        assert callable(register_routers)
