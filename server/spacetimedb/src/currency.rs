use crate::invoice::*;
use spacetimedb::*;

/// ISO 4217 currency codes supported by the CRM.
/// Keep in sync with the frontend currency pickers
/// (web/src/pages/InvoicesPage.tsx, PaymentsPage.tsx, EstimatesPage.tsx,
/// PurchaseOrdersPage.tsx, POS page).
pub const SUPPORTED_CURRENCIES: [&str; 4] = ["USD", "EUR", "GBP", "CAD"];

/// Validate a currency code.
///
/// Only exact uppercase ISO 4217 codes from [`SUPPORTED_CURRENCIES`] are
/// accepted, so entity currency fields (Invoice, Estimate, PurchaseOrder,
/// CounterSale, Payment) can never diverge into junk values that would make
/// cross-entity comparisons ambiguous.
pub(crate) fn validate_currency(currency: &str) -> Result<(), String> {
    if SUPPORTED_CURRENCIES.contains(&currency) {
        Ok(())
    } else {
        Err(format!(
            "Unsupported currency '{currency}': must be one of {}",
            SUPPORTED_CURRENCIES.join(", ")
        ))
    }
}

/// Enforce that a payment is recorded in the same currency as the invoice it
/// pays. This is the reducer-level consistency check for the multi-currency
/// feature: a payment in USD can no longer silently settle an invoice in EUR.
///
/// Payments without an invoice link (`invoice_id` empty) or referencing an
/// invoice that no longer exists are allowed — there is nothing to be
/// inconsistent with, and this preserves legacy behavior for unlinked payments.
pub(crate) fn ensure_payment_matches_invoice(
    ctx: &ReducerContext,
    invoice_id: &str,
    payment_currency: &str,
) -> Result<(), String> {
    if invoice_id.is_empty() {
        return Ok(());
    }
    let invoice_id_owned = invoice_id.to_string();
    if let Some(invoice) = ctx.db.invoices().id().find(&invoice_id_owned) {
        if invoice.currency != payment_currency {
            return Err(format!(
                "Currency mismatch: payment is in {payment_currency} but invoice {invoice_id} is in {}",
                invoice.currency
            ));
        }
    }
    Ok(())
}
