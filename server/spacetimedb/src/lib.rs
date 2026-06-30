#![allow(clippy::too_many_arguments)]

use spacetimedb::*;

pub mod customer;
pub mod ticket;
pub mod payment;
pub mod appointment;
pub mod product;
pub mod purchase_order;
pub mod inventory;
pub mod tax_rate;
pub mod user;
pub mod audit;
pub mod custom_field;
pub mod customer_geolocation;
pub mod checklist;
pub mod pos;
pub mod webhook;
pub mod tenant;
#[cfg(test)]
pub mod customer_test;

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
pub use pos::*;
pub use audit::*;
pub use custom_field::*;
pub use webhook::*;

// ─── Recurring Invoice Rule ──

#[spacetimedb::table(accessor = recurring_invoice_rules, public)]
#[derive(Debug, Clone)]
pub struct RecurringInvoiceRule {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub customer_id: String,
    pub name: String,
    pub frequency: String,
    pub interval_count: u32,
    pub next_generation_date: u64,
    pub last_generated_date: u64,
    pub due_date_days: u32,
    pub line_items_json: String,
    pub status: String,
    pub created_at: u64,
    pub updated_at: u64,
}

// ─── Saved Payment Method ──

#[spacetimedb::table(accessor = saved_payment_methods, public)]
#[derive(Debug, Clone)]
pub struct SavedPaymentMethod {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub customer_id: String,
    pub stripe_payment_method_id: String,
    pub brand: String,
    pub last4: String,
    pub exp_month: u32,
    pub exp_year: u32,
    pub is_default: bool,
    pub created_at: u64,
    pub updated_at: u64,
}

// ─── Scheduled Report ──

#[spacetimedb::table(accessor = scheduled_reports, public)]
#[derive(Debug, Clone)]
pub struct ScheduledReport {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub name: String,
    pub report_type: String,
    pub schedule_frequency: String,
    pub schedule_config_json: String,
    pub recipients_json: String,
    pub filters_json: String,
    pub next_run_at: u64,
    pub last_run_at: u64,
    pub last_error: String,
    pub enabled: bool,
    pub created_at: u64,
    pub updated_at: u64,
}

// ─── Invoice + Estimate (defined in lib.rs to avoid cross-module accessor issues) ──

#[spacetimedb::table(accessor = invoices, public)]
#[derive(Debug, Clone)]
pub struct Invoice {
    #[primary_key]
    pub id: String,
    #[index(btree)]
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
    pub currency: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::table(accessor = invoice_line_items, public)]
#[derive(Debug, Clone)]
pub struct InvoiceLineItem {
    #[primary_key]
    pub id: String,
    #[index(btree)]
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
    #[index(btree)]
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
    pub currency: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::table(accessor = estimate_line_items, public)]
#[derive(Debug, Clone)]
pub struct EstimateLineItem {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub estimate_id: String,
    pub item_type: String,
    pub description: String,
    pub quantity: f64,
    pub unit_price: f64,
    pub total: f64,
    pub sort_order: u32,
}

// ─── Recurring Invoice Rule reducers ──

#[spacetimedb::reducer]
pub fn create_recurring_invoice_rule(
    ctx: &ReducerContext,
    tenant_id: String,
    customer_id: String,
    name: String,
    frequency: String,
    interval_count: u32,
    due_date_days: u32,
    line_items_json: String,
    next_generation_date: u64,
) {
    let id = make_id("rir", ctx);
    let now = now_ms(ctx);
    ctx.db.recurring_invoice_rules().insert(RecurringInvoiceRule {
        id,
        tenant_id,
        customer_id,
        name,
        frequency,
        interval_count,
        next_generation_date,
        last_generated_date: 0,
        due_date_days,
        line_items_json,
        status: "active".to_string(),
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_recurring_invoice_rule(
    ctx: &ReducerContext,
    id: String,
    name: String,
    frequency: String,
    interval_count: u32,
    due_date_days: u32,
    line_items_json: String,
    next_generation_date: u64,
    status: String,
) {
    if let Some(rule) = ctx.db.recurring_invoice_rules().id().find(&id) {
        ctx.db.recurring_invoice_rules().id().update(RecurringInvoiceRule {
            name,
            frequency,
            interval_count,
            due_date_days,
            line_items_json,
            next_generation_date,
            status,
            updated_at: now_ms(ctx),
            ..rule
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_recurring_invoice_rule(ctx: &ReducerContext, id: String) {
    ctx.db.recurring_invoice_rules().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn generate_recurring_invoices(ctx: &ReducerContext) {
    let now = now_ms(ctx);
    let mut invoice_counter: u64 = 0;

    // Collect all active rules whose next generation date is now or in the past
    let due_rules: Vec<RecurringInvoiceRule> = ctx
        .db
        .recurring_invoice_rules()
        .iter()
        .filter(|r| r.status == "active" && r.next_generation_date > 0 && r.next_generation_date <= now)
        .collect();

    for rule in due_rules {
        // Skip if customer data is missing
        let _customer_id = rule.customer_id.clone();
        if _customer_id.is_empty() {
            continue;
        }

        // Calculate next generation date based on frequency
        let ms_per_day: u64 = 86400000;
        let next_gen = match rule.frequency.as_str() {
            "daily" => now + ms_per_day * rule.interval_count as u64,
            "weekly" => now + ms_per_day * 7 * rule.interval_count as u64,
            "biweekly" => now + ms_per_day * 14 * rule.interval_count as u64,
            "monthly" => now + ms_per_day * 30 * rule.interval_count as u64,
            "quarterly" => now + ms_per_day * 90 * rule.interval_count as u64,
            "yearly" => now + ms_per_day * 365 * rule.interval_count as u64,
            _ => now + ms_per_day * 30,
        };

        // Create invoice
        let inv_id = format!("ririnv_{}_{}", now, invoice_counter);
        invoice_counter += 1;
        let invoice_number = ctx.db.invoices().iter().count() as u64 + 10001;
        let due_date = now + rule.due_date_days as u64 * ms_per_day;

        ctx.db.invoices().insert(Invoice {
            id: inv_id.clone(),
            tenant_id: rule.tenant_id.clone(),
            customer_id: rule.customer_id.clone(),
            ticket_id: String::new(),
            invoice_number,
            status: "draft".to_string(),
            subtotal: 0.0,
            tax_rate: 0.0,
            tax_amount: 0.0,
            total: 0.0,
            discount_amount: 0.0,
            discount_percent: 0.0,
            notes: format!("Auto-generated from recurring rule: {}", rule.name),
            terms: String::new(),
            due_date,
            currency: "USD".to_string(),
            created_at: now,
            updated_at: now,
        });

        // Parse line items JSON and insert
        if let Ok(items) = serde_json::from_str::<Vec<serde_json::Value>>(&rule.line_items_json) {
            for (i, item) in items.iter().enumerate() {
                let desc = item.get("description").and_then(|v| v.as_str()).unwrap_or("Item").to_string();
                let qty = item.get("quantity").and_then(|v| v.as_f64()).unwrap_or(1.0);
                let price = item.get("unit_price").and_then(|v| v.as_f64()).unwrap_or(0.0);
                let total = qty * price;
                let li_id = format!("riln_{}_{}_{}", now, invoice_counter - 1, i);
                ctx.db.invoice_line_items().insert(InvoiceLineItem {
                    id: li_id,
                    tenant_id: rule.tenant_id.clone(),
                    invoice_id: inv_id.clone(),
                    item_type: item.get("item_type").and_then(|v| v.as_str()).unwrap_or("service").to_string(),
                    description: desc,
                    quantity: qty,
                    unit_price: price,
                    total,
                    sort_order: i as u32,
                });
            }

            // Recalc invoice totals
            if let Some(inv) = ctx.db.invoices().id().find(&inv_id) {
                let items: Vec<InvoiceLineItem> = ctx
                    .db
                    .invoice_line_items()
                    .iter()
                    .filter(|i| i.invoice_id == inv_id)
                    .collect();
                let subtotal: f64 = items.iter().map(|i| i.total).sum();
                let tax_amount = subtotal * inv.tax_rate / 100.0;
                let total = subtotal + tax_amount - inv.discount_amount;
                ctx.db.invoices().id().update(Invoice {
                    subtotal,
                    tax_amount,
                    total,
                    updated_at: now,
                    ..inv
                });
            }
        }

        // Update rule: set next generation date and last generated date
        ctx.db.recurring_invoice_rules().id().update(RecurringInvoiceRule {
            next_generation_date: next_gen,
            last_generated_date: now,
            updated_at: now,
            ..rule
        });
    }
}

// ─── Saved Payment Method reducers ──

#[spacetimedb::reducer]
pub fn save_payment_method(
    ctx: &ReducerContext,
    tenant_id: String,
    customer_id: String,
    stripe_payment_method_id: String,
    brand: String,
    last4: String,
    exp_month: u32,
    exp_year: u32,
) {
    let id = make_id("pm", ctx);
    let now = now_ms(ctx);
    // Check if this is the first method for this customer — make it default
    let existing = ctx.db.saved_payment_methods().iter()
        .filter(|m| m.customer_id == customer_id)
        .count();
    ctx.db.saved_payment_methods().insert(SavedPaymentMethod {
        id,
        tenant_id,
        customer_id,
        stripe_payment_method_id,
        brand,
        last4,
        exp_month,
        exp_year,
        is_default: existing == 0,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn set_default_payment_method(ctx: &ReducerContext, id: String, customer_id: String) {
    let now = now_ms(ctx);
    // Unset all defaults for this customer
    let methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter()
        .filter(|m| m.customer_id == customer_id)
        .collect();
    for m in &methods {
        ctx.db.saved_payment_methods().id().update(SavedPaymentMethod {
            is_default: m.id == id,
            updated_at: now,
            ..m.clone()
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_payment_method(ctx: &ReducerContext, id: String) {
    ctx.db.saved_payment_methods().id().delete(&id);
}

// ─── Scheduled Report reducers ──

#[spacetimedb::reducer]
pub fn create_scheduled_report(
    ctx: &ReducerContext,
    tenant_id: String,
    name: String,
    report_type: String,
    schedule_frequency: String,
    schedule_config_json: String,
    recipients_json: String,
    filters_json: String,
    next_run_at: u64,
) {
    let id = make_id("srpt", ctx);
    let now = now_ms(ctx);
    ctx.db.scheduled_reports().insert(ScheduledReport {
        id,
        tenant_id,
        name,
        report_type,
        schedule_frequency,
        schedule_config_json,
        recipients_json,
        filters_json,
        next_run_at,
        last_run_at: 0,
        last_error: String::new(),
        enabled: true,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_scheduled_report(
    ctx: &ReducerContext,
    id: String,
    name: String,
    report_type: String,
    schedule_frequency: String,
    schedule_config_json: String,
    recipients_json: String,
    filters_json: String,
    next_run_at: u64,
    enabled: bool,
) {
    if let Some(r) = ctx.db.scheduled_reports().id().find(&id) {
        ctx.db.scheduled_reports().id().update(ScheduledReport {
            name,
            report_type,
            schedule_frequency,
            schedule_config_json,
            recipients_json,
            filters_json,
            next_run_at,
            enabled,
            updated_at: now_ms(ctx),
            ..r
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_scheduled_report(ctx: &ReducerContext, id: String) {
    ctx.db.scheduled_reports().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn mark_report_run(ctx: &ReducerContext, id: String, next_run_at: u64) {
    if let Some(r) = ctx.db.scheduled_reports().id().find(&id) {
        ctx.db.scheduled_reports().id().update(ScheduledReport {
            last_run_at: now_ms(ctx),
            next_run_at,
            last_error: String::new(),
            updated_at: now_ms(ctx),
            ..r
        });
    }
}

#[spacetimedb::reducer]
pub fn mark_report_error(ctx: &ReducerContext, id: String, error: String) {
    if let Some(r) = ctx.db.scheduled_reports().id().find(&id) {
        ctx.db.scheduled_reports().id().update(ScheduledReport {
            last_error: error,
            updated_at: now_ms(ctx),
            ..r
        });
    }
}

// ─── Invoice reducers ──

#[spacetimedb::reducer]
pub fn create_invoice(ctx: &ReducerContext, tenant_id: String, customer_id: String, ticket_id: String, notes: String, terms: String, due_date: u64, currency: String) {
    let id = make_id("inv", ctx);
    let now = now_ms(ctx);
    let invoice_number = ctx.db.invoices().iter().count() as u64 + 10001;
    ctx.db.invoices().insert(Invoice {
        id, tenant_id, customer_id, ticket_id, invoice_number,
        status: "draft".to_string(),
        subtotal: 0.0, tax_rate: 0.0, tax_amount: 0.0, total: 0.0,
        discount_amount: 0.0, discount_percent: 0.0,
        notes, terms, due_date, currency, created_at: now, updated_at: now,
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
pub fn create_estimate(ctx: &ReducerContext, tenant_id: String, customer_id: String, ticket_id: String, notes: String, expires_at: u64, currency: String) {
    let id = make_id("est", ctx);
    let now = now_ms(ctx);
    let estimate_number = ctx.db.estimates().iter().count() as u64 + 1001;
    ctx.db.estimates().insert(Estimate {
        id, tenant_id, customer_id, ticket_id, estimate_number,
        status: "draft".to_string(),
        subtotal: 0.0, tax_rate: 0.0, tax_amount: 0.0, total: 0.0, discount_amount: 0.0,
        notes, expires_at, invoice_id: String::new(), currency, created_at: now, updated_at: now,
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
            currency: "USD".to_string(),
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
