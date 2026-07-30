#![allow(clippy::too_many_arguments)]

use spacetimedb::*;

// FFI stub implementations for native test builds (non-WASM).
// Provides an in-memory datastore so tests using ReducerContext::__dummy() can run.
#[cfg(all(test, not(target_arch = "wasm32")))]
pub mod test_stubs;

pub mod appointment;
#[cfg(test)]
pub mod appointment_test;
pub mod audit;
#[cfg(test)]
pub mod audit_test;
pub mod checklist;
#[cfg(test)]
pub mod checklist_test;
#[cfg(test)]
pub mod container_test;
pub mod custom_field;
#[cfg(test)]
pub mod custom_field_test;
pub mod customer;
pub mod customer_geolocation;
#[cfg(test)]
pub mod customer_geolocation_test;
#[cfg(test)]
pub mod customer_import_test;
#[cfg(test)]
pub mod customer_test;
pub mod estimate;
#[cfg(test)]
pub mod estimate_test;
pub mod inventory;
#[cfg(test)]
pub mod inventory_adjustment_test;
pub mod invoice;
#[cfg(test)]
pub mod invoice_test;
#[cfg(test)]
pub mod lib_test;
pub mod payment;
#[cfg(test)]
pub mod payment_test;
pub mod pos;
#[cfg(test)]
pub mod pos_test;
pub mod product;
#[cfg(test)]
pub mod product_test;
pub mod purchase_order;
#[cfg(test)]
pub mod purchase_order_test;
pub mod push_subscription;
pub mod recurring_invoice_rule;
#[cfg(test)]
pub mod recurring_invoice_test;
#[cfg(test)]
pub mod safety_test;
pub mod saved_payment_method;
#[cfg(test)]
pub mod saved_payment_method_test;
pub mod scheduled_report;
#[cfg(test)]
pub mod scheduled_report_test;
pub mod sla_config;
#[cfg(test)]
pub mod sla_config_test;
pub mod tax_rate;
#[cfg(test)]
pub mod tax_rate_test;
pub mod tenant;
#[cfg(test)]
pub mod tenant_test;
pub mod ticket;
#[cfg(test)]
pub mod ticket_test;
pub mod user;
#[cfg(test)]
pub mod user_test;
pub mod webhook;
#[cfg(test)]
pub mod webhook_test;

pub use appointment::*;
pub use audit::*;
pub use checklist::*;
pub use custom_field::*;
pub use customer::*;
pub use customer_geolocation::*;
pub use estimate::*;
pub use inventory::*;
pub use invoice::*;
pub use payment::*;
pub use pos::*;
pub use product::*;
pub use purchase_order::*;
pub use recurring_invoice_rule::*;
pub use saved_payment_method::*;
pub use scheduled_report::*;
pub use sla_config::*;
pub use tax_rate::*;
pub use tenant::*;
pub use ticket::*;
pub use user::*;
pub use webhook::*;

// ─── Helpers ──

pub(crate) fn now_ms(ctx: &ReducerContext) -> u64 {
    ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000
}

pub(crate) fn make_id(prefix: &str, ctx: &ReducerContext) -> String {
    let ts = now_ms(ctx);
    let discrim = ctx.sender().to_hex();
    let short = if discrim.len() > 8 {
        &discrim[..8]
    } else {
        &discrim
    };
    format!("{}_{}_{}", prefix, ts, short)
}
