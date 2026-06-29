#![allow(clippy::too_many_arguments)]

use spacetimedb::*;

mod customer;
mod ticket;
mod payment;
mod appointment;
mod product;
mod purchase_order;
mod inventory;
mod tax_rate;
mod user;
mod audit;
mod custom_field;
mod customer_geolocation;
mod checklist;
mod webhook;
mod tenant;

pub use customer::*;
pub use customer_geolocation::*;
pub use checklist::*;
pub use ticket::*;
pub use payment::*;
pub use appointment::*;
pub use product::*;
pub use purchase_order::*;
pub use inventory::*;
pub use tax_rate::*;
pub use user::*;
pub use audit::*;
pub use custom_field::*;
pub use webhook::*;

// ─── Invoice + Estimate (defined in lib.rs to avoid cross-module accessor issues) ──

#[spacetimedb::table(accessor = invoices, public)]
#[derive(Debug, Clone)]
pub struct Invoice {
    #[primary_key]
    pub id: String,
    pub tenant_id: String,
    pub customer_id: String,
    pub ticket_id: String,
    pub invoice_number: u64,
    pub status: String,
    pub subtotal: f64,
    pub tax_rate: f64,
    pub tax_amount: f64,
    pub total: f64,
    pub discount_amount: f64,
    pub discount_percent: f64,
    pub notes: String,
    pub terms: String,
    pub due_date: u64,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::table(accessor = invoice_line_items, public)]
#[derive(Debug, Clone)]
pub struct InvoiceLineItem {
    #[primary_key]
    pub id: String,
    pub tenant_id: String,
    pub invoice_id: String,
    pub item_type: String,
    pub description: String,
    pub quantity: f64,
    pub unit_price: f64,
    pub total: f64,
    pub sort_order: u32,
}

#[spacetimedb::table(accessor = estimates, public)]
#[derive(Debug, Clone)]
pub struct Estimate {
    #[primary_key]
    pub id: String,
    pub tenant_id: String,
    pub customer_id: String,
    pub ticket_id: String,
    pub estimate_number: u64,
    pub status: String,
    pub subtotal: f64,
    pub tax_rate: f64,
    pub tax_amount: f64,
    pub total: f64,
    pub discount_amount: f64,
    pub notes: String,
    pub expires_at: u64,
    pub invoice_id: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::table(accessor = estimate_line_items, public)]
#[derive(Debug, Clone)]
pub struct EstimateLineItem {
    #[primary_key]
    pub id: String,
    pub tenant_id: String,
    pub estimate_id: String,
    pub item_type: String,
    pub description: String,
    pub quantity: f64,
    pub unit_price: f64,
    pub total: f64,
    pub sort_order: u32,
}

// ─── Reducers ──

#[spacetimedb::reducer]
pub fn create_invoice(ctx: &ReducerContext, tenant_id: String, customer_id: String, ticket_id: String, notes: String, terms: String, due_date: u64) {
    let id = make_id("inv", ctx);
    let now = now_ms(ctx);
    let invoice_number = ctx.db.invoices().iter().count() as u64 + 10001;
    ctx.db.invoices().insert(Invoice {
        id, tenant_id, customer_id, ticket_id, invoice_number,
        status: "draft".to_string(),
        subtotal: 0.0, tax_rate: 0.0, tax_amount: 0.0, total: 0.0,
        discount_amount: 0.0, discount_percent: 0.0,
        notes, terms, due_date, created_at: now, updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_invoice_status(ctx: &ReducerContext, id: String, status: String) {
    if let Some(inv) = ctx.db.invoices().id().find(&id) {
        ctx.db.invoices().id().update(Invoice { status, ..inv });
    }
}

#[spacetimedb::reducer]
pub fn add_invoice_line_item(ctx: &ReducerContext, invoice_id: String, item_type: String, description: String, quantity: f64, unit_price: f64) {
    let id = make_id("iln", ctx);
    let total = quantity * unit_price;
    let sort = ctx.db.invoice_line_items().iter().filter(|i| i.invoice_id == invoice_id).count() as u32;
    // Derive tenant_id from the parent invoice
    let tenant_id = ctx.db.invoices().id().find(&invoice_id).map_or(String::new(), |inv| inv.tenant_id.clone());
    ctx.db.invoice_line_items().insert(InvoiceLineItem { id, tenant_id, invoice_id: invoice_id.clone(), item_type, description, quantity, unit_price, total, sort_order: sort });
    // Recalc invoice totals
    if let Some(inv) = ctx.db.invoices().id().find(&invoice_id) {
        let items: Vec<InvoiceLineItem> = ctx
            .db
            .invoice_line_items()
            .iter()
            .filter(|i| i.invoice_id == invoice_id)
            .collect();
        let subtotal: f64 = items.iter().map(|i| i.total).sum();
        let tax_amount = subtotal * inv.tax_rate / 100.0;
        let total = subtotal + tax_amount - inv.discount_amount;
        ctx.db.invoices().id().update(Invoice {
            subtotal,
            tax_amount,
            total,
            updated_at: now_ms(ctx),
            ..inv
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_invoice_line_item(ctx: &ReducerContext, id: String) {
    ctx.db.invoice_line_items().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn delete_invoice(ctx: &ReducerContext, id: String) {
    ctx.db.invoices().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn set_invoice_tax_rate(ctx: &ReducerContext, id: String, tax_rate: f64) {
    if let Some(inv) = ctx.db.invoices().id().find(&id) {
        let tax_amount = inv.subtotal * tax_rate / 100.0;
        let total = inv.subtotal + tax_amount - inv.discount_amount;
        ctx.db.invoices().id().update(Invoice {
            tax_rate,
            tax_amount,
            total,
            updated_at: now_ms(ctx),
            ..inv
        });
    }
}


// ─── Estimate reducers ──

#[spacetimedb::reducer]
pub fn create_estimate(ctx: &ReducerContext, tenant_id: String, customer_id: String, ticket_id: String, notes: String, expires_at: u64) {
    let id = make_id("est", ctx);
    let now = now_ms(ctx);
    let estimate_number = ctx.db.estimates().iter().count() as u64 + 1001;
    ctx.db.estimates().insert(Estimate {
        id, tenant_id, customer_id, ticket_id, estimate_number,
        status: "draft".to_string(),
        subtotal: 0.0, tax_rate: 0.0, tax_amount: 0.0, total: 0.0, discount_amount: 0.0,
        notes, expires_at, invoice_id: String::new(), created_at: now, updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_estimate_status(ctx: &ReducerContext, id: String, status: String) {
    if let Some(e) = ctx.db.estimates().id().find(&id) {
        ctx.db.estimates().id().update(Estimate { status, ..e });
    }
}

#[spacetimedb::reducer]
pub fn add_estimate_line_item(ctx: &ReducerContext, estimate_id: String, item_type: String, description: String, quantity: f64, unit_price: f64) {
    let id = make_id("eln", ctx);
    let total = quantity * unit_price;
    let sort = ctx.db.estimate_line_items().iter().filter(|i| i.estimate_id == estimate_id).count() as u32;
    let tenant_id = ctx.db.estimates().id().find(&estimate_id).map_or(String::new(), |est| est.tenant_id.clone());
    ctx.db.estimate_line_items().insert(EstimateLineItem { id, tenant_id, estimate_id: estimate_id.clone(), item_type, description, quantity, unit_price, total, sort_order: sort });
    if let Some(est) = ctx.db.estimates().id().find(&estimate_id) {
        let items: Vec<EstimateLineItem> = ctx.db.estimate_line_items().iter().filter(|i| i.estimate_id == estimate_id).collect();
        let subtotal: f64 = items.iter().map(|i| i.total).sum();
        let tax_amount = subtotal * est.tax_rate / 100.0;
        ctx.db.estimates().id().update(Estimate { subtotal, tax_amount, total: subtotal + tax_amount - est.discount_amount, updated_at: now_ms(ctx), ..est });
    }
}

#[spacetimedb::reducer]
pub fn delete_estimate(ctx: &ReducerContext, id: String) {
    ctx.db.estimates().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn convert_estimate_to_invoice(ctx: &ReducerContext, estimate_id: String) {
    if let Some(est) = ctx.db.estimates().id().find(&estimate_id) {
        let now = now_ms(ctx);
        // Create invoice from estimate
        let inv_id = make_id("inv", ctx);
        let invoice_number = ctx.db.invoices().iter().count() as u64 + 10001;
        ctx.db.invoices().insert(Invoice {
            id: inv_id.clone(),
            tenant_id: est.tenant_id.clone(),
            customer_id: est.customer_id.clone(),
            ticket_id: est.ticket_id.clone(),
            invoice_number,
            status: "draft".to_string(),
            subtotal: est.subtotal,
            tax_rate: est.tax_rate,
            tax_amount: est.tax_amount,
            total: est.total,
            discount_amount: est.discount_amount,
            discount_percent: 0.0,
            notes: est.notes.clone(),
            terms: String::new(),
            due_date: 0,
            created_at: now,
            updated_at: now,
        });
        // Copy line items with unique IDs (add counter to avoid same-tick collision)
        let mut li_idx = 0u64;
        for item in ctx.db.estimate_line_items().iter().filter(|i| i.estimate_id == estimate_id) {
            let li_id = format!("iln_{}_{}_{}", now, li_idx, ctx.sender().to_hex().chars().take(8).collect::<String>());
            li_idx += 1;
            ctx.db.invoice_line_items().insert(InvoiceLineItem {
                id: li_id,
                tenant_id: est.tenant_id.clone(),
                invoice_id: inv_id.clone(),
                item_type: item.item_type.clone(),
                description: item.description.clone(),
                quantity: item.quantity,
                unit_price: item.unit_price,
                total: item.total,
                sort_order: item.sort_order,
            });
        }
        // Mark estimate as approved and link to invoice
        ctx.db.estimates().id().update(Estimate {
            status: "approved".to_string(),
            invoice_id: inv_id.clone(),
            updated_at: now,
            ..est
        });
    }
}

// ─── Helpers ──

fn now_ms(ctx: &ReducerContext) -> u64 {
    ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000
}

fn make_id(prefix: &str, ctx: &ReducerContext) -> String {
    let ts = now_ms(ctx);
    let discrim = ctx.sender().to_hex();
    let short = if discrim.len() > 8 { &discrim[..8] } else { &discrim };
    format!("{}_{}_{}", prefix, ts, short)
}
