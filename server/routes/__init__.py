"""Route registrations for SpacetimeCRM."""
from __future__ import annotations


def register_routers(app):
    """Import and register all APIRouter modules on the app."""
    from . import (
        auth, appointments, checklists, custom_fields, customers,
        dashboard, estimates, export_import, health, invoices,
        payment_methods, payments, portal, products, purchase_orders,
        recurring_invoices, report_schedules, settings, tax_rates, tenants, tickets, users,
        webhooks,
    )

    app.include_router(auth.router)
    app.include_router(appointments.router)
    app.include_router(checklists.router)
    app.include_router(custom_fields.router)
    app.include_router(customers.router)
    app.include_router(dashboard.router)
    app.include_router(estimates.router)
    app.include_router(export_import.router)
    app.include_router(health.router)
    app.include_router(invoices.router)
    app.include_router(payments.router)
    app.include_router(payment_methods.router)
    app.include_router(portal.router)
    app.include_router(products.router)
    app.include_router(purchase_orders.router)
    app.include_router(recurring_invoices.router)
    app.include_router(report_schedules.router)
    app.include_router(settings.router)
    app.include_router(tax_rates.router)
    app.include_router(tenants.router)
    app.include_router(tickets.router)
    app.include_router(users.router)
    app.include_router(webhooks.router)
