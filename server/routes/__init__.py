"""Route registrations for SpacetimeCRM."""

from __future__ import annotations

from routes.appointments import router as appointments_router
from routes.auth import router as auth_router
from routes.checklists import router as checklists_router
from routes.custom_fields import router as custom_fields_router
from routes.customers import router as customers_router
from routes.dashboard import router as dashboard_router
from routes.estimates import router as estimates_router
from routes.export_import import router as export_import_router
from routes.health import router as health_router
from routes.invoices import router as invoices_router
from routes.payment_methods import router as payment_methods_router
from routes.payments import router as payments_router
from routes.portal import router as portal_router
from routes.pos import router as pos_router
from routes.products import router as products_router
from routes.purchase_orders import router as purchase_orders_router
from routes.push import router as push_router
from routes.recurring_invoices import router as recurring_invoices_router
from routes.report_schedules import router as report_schedules_router
from routes.settings import router as settings_router
from routes.tax_rates import router as tax_rates_router
from routes.tenants import router as tenants_router
from routes.tickets import router as tickets_router
from routes.users import router as users_router
from routes.webhooks import router as webhooks_router


def register_routers(app):
    """Import and register all APIRouter modules on the app."""
    app.include_router(auth_router)
    app.include_router(appointments_router)
    app.include_router(checklists_router)
    app.include_router(custom_fields_router)
    app.include_router(customers_router)
    app.include_router(dashboard_router)
    app.include_router(estimates_router)
    app.include_router(export_import_router)
    app.include_router(health_router)
    app.include_router(invoices_router)
    app.include_router(payments_router)
    app.include_router(payment_methods_router)
    app.include_router(portal_router)
    app.include_router(pos_router)
    app.include_router(products_router)
    app.include_router(purchase_orders_router)
    app.include_router(push_router)
    app.include_router(recurring_invoices_router)
    app.include_router(report_schedules_router)
    app.include_router(settings_router)
    app.include_router(tax_rates_router)
    app.include_router(tenants_router)
    app.include_router(tickets_router)
    app.include_router(users_router)
    app.include_router(webhooks_router)
