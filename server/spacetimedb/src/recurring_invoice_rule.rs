use spacetimedb::*;

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
    let id = super::make_id("rir", ctx);
    let now = super::now_ms(ctx);
    ctx.db
        .recurring_invoice_rules()
        .insert(RecurringInvoiceRule {
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
    tenant_id: String,
    name: String,
    frequency: String,
    interval_count: u32,
    due_date_days: u32,
    line_items_json: String,
    next_generation_date: u64,
    status: String,
) {
    if let Some(rule) = ctx.db.recurring_invoice_rules().id().find(&id) {
        // Tenant isolation: only the owning tenant may update the rule.
        if rule.tenant_id != tenant_id {
            return;
        }
        ctx.db
            .recurring_invoice_rules()
            .id()
            .update(RecurringInvoiceRule {
                name,
                frequency,
                interval_count,
                due_date_days,
                line_items_json,
                next_generation_date,
                status,
                updated_at: super::now_ms(ctx),
                ..rule
            });
    }
}

#[spacetimedb::reducer]
pub fn delete_recurring_invoice_rule(ctx: &ReducerContext, id: String, tenant_id: String) {
    // Tenant isolation: only the owning tenant may delete the rule.
    if let Some(rule) = ctx.db.recurring_invoice_rules().id().find(&id) {
        if rule.tenant_id == tenant_id {
            ctx.db.recurring_invoice_rules().id().delete(&id);
        }
    }
}

#[spacetimedb::reducer]
pub fn generate_recurring_invoices(ctx: &ReducerContext, tenant_id: String) {
    use crate::invoice::*;

    let now = super::now_ms(ctx);
    let mut invoice_counter: u64 = 0;

    // Collect all active rules for THIS tenant whose next generation date is now or in the past
    let due_rules: Vec<RecurringInvoiceRule> = ctx
        .db
        .recurring_invoice_rules()
        .iter()
        .filter(|r| {
            r.tenant_id == tenant_id
                && r.status == "active"
                && r.next_generation_date > 0
                && r.next_generation_date <= now
        })
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
                let desc = item
                    .get("description")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Item")
                    .to_string();
                let qty = item.get("quantity").and_then(|v| v.as_f64()).unwrap_or(1.0);
                let price = item
                    .get("unit_price")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.0);
                let total = qty * price;
                let li_id = format!("riln_{}_{}_{}", now, invoice_counter - 1, i);
                ctx.db.invoice_line_items().insert(InvoiceLineItem {
                    id: li_id,
                    tenant_id: rule.tenant_id.clone(),
                    invoice_id: inv_id.clone(),
                    item_type: item
                        .get("item_type")
                        .and_then(|v| v.as_str())
                        .unwrap_or("service")
                        .to_string(),
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
        ctx.db
            .recurring_invoice_rules()
            .id()
            .update(RecurringInvoiceRule {
                next_generation_date: next_gen,
                last_generated_date: now,
                updated_at: now,
                ..rule
            });
    }
}

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_create_rule() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(
            &ctx,
            "t_1".into(),
            "cust_1".into(),
            "Monthly Service".into(),
            "monthly".into(),
            1,
            30,
            r#"[{"description":"Support","quantity":1,"unit_price":99.99}]"#.into(),
            1700000000000,
        );
        let rules: Vec<RecurringInvoiceRule> = ctx.db.recurring_invoice_rules().iter().collect();
        assert_eq!(rules.len(), 1);
        let r = &rules[0];
        assert!(
            r.id.starts_with("rir_"),
            "id should start with 'rir_', got: {}",
            r.id
        );
        assert_eq!(r.status, "active");
        assert!(r.next_generation_date > 0);
        assert_eq!(r.last_generated_date, 0);
        assert_eq!(r.name, "Monthly Service");
        assert_eq!(r.frequency, "monthly");
        assert!(r.created_at > 0);
        assert_eq!(r.created_at, r.updated_at);
    }

    #[test]
    fn test_update_rule() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(
            &ctx,
            "t_1".into(),
            "cust_1".into(),
            "Original".into(),
            "weekly".into(),
            1,
            14,
            String::new(),
            1700000000000,
        );
        let id = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .next()
            .expect("expected rule to exist")
            .id
            .clone();
        update_recurring_invoice_rule(
            &ctx,
            id.clone(),
            "t_1".into(),
            "Updated Name".into(),
            "monthly".into(),
            2,
            45,
            r#"[{"description":"New item","quantity":2,"unit_price":50.00}]"#.into(),
            1700100000000,
            "paused".into(),
        );
        let updated = ctx
            .db
            .recurring_invoice_rules()
            .id()
            .find(&id)
            .expect("expected rule to exist");
        assert_eq!(updated.name, "Updated Name");
        assert_eq!(updated.frequency, "monthly");
        assert_eq!(updated.interval_count, 2);
        assert_eq!(updated.due_date_days, 45);
        assert_eq!(updated.status, "paused");
        assert_eq!(updated.next_generation_date, 1700100000000);
        assert!(updated.updated_at > updated.created_at);
    }

    #[test]
    fn test_delete_rule() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(
            &ctx,
            "t_1".into(),
            "cust_1".into(),
            "Delete Me".into(),
            "daily".into(),
            1,
            0,
            String::new(),
            1700000000000,
        );
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 1);
        let id = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .next()
            .expect("expected rule to exist")
            .id
            .clone();
        delete_recurring_invoice_rule(&ctx, id, "t_1".into());
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 0);
    }

    #[test]
    fn test_generate_invoices() {
        let ctx = test_ctx();
        // Create a rule with next_generation_date in the past
        create_recurring_invoice_rule(
            &ctx,
            "t_1".into(),
            "cust_1".into(),
            "Auto Invoice".into(),
            "monthly".into(),
            1,
            30,
            String::new(),
            1000, // past timestamp
        );
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 1);
        let rule_id = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .next()
            .expect("expected rule to exist")
            .id
            .clone();
        let old_gen_date = ctx
            .db
            .recurring_invoice_rules()
            .id()
            .find(&rule_id)
            .expect("expected rule to exist")
            .next_generation_date;

        generate_recurring_invoices(&ctx, "t_1".into());

        // An invoice should have been created
        use crate::invoice::invoices;
        let invoices: Vec<crate::invoice::Invoice> = ctx.db.invoices().iter().collect();
        assert_eq!(invoices.len(), 1, "should have created one invoice");

        // The rule's next_generation_date should have advanced
        let updated_rule = ctx
            .db
            .recurring_invoice_rules()
            .id()
            .find(&rule_id)
            .expect("expected rule to exist");
        assert!(
            updated_rule.next_generation_date > old_gen_date,
            "next_generation_date should advance: old={}, new={}",
            old_gen_date,
            updated_rule.next_generation_date
        );
        assert!(
            updated_rule.last_generated_date > 0,
            "last_generated_date should be set"
        );
    }

    #[test]
    fn test_generate_invoices_no_due() {
        let ctx = test_ctx();
        // Create a rule with future next_generation_date
        create_recurring_invoice_rule(
            &ctx,
            "t_1".into(),
            "cust_1".into(),
            "Future Invoice".into(),
            "monthly".into(),
            1,
            30,
            String::new(),
            999999999999999, // far future
        );
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 1);

        generate_recurring_invoices(&ctx, "t_1".into());

        // No invoice should have been created
        use crate::invoice::invoices;
        let invoices: Vec<crate::invoice::Invoice> = ctx.db.invoices().iter().collect();
        assert_eq!(
            invoices.len(),
            0,
            "no invoices should be created for future rules"
        );

        // Rule should be unchanged
        let rule = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .next()
            .expect("expected rule to exist");
        assert_eq!(
            rule.last_generated_date, 0,
            "last_generated_date should remain 0"
        );
    }

    #[test]
    fn test_generate_invoice_with_items() {
        let ctx = test_ctx();
        let items_json = r#"[
            {"description":"Screen Repair","quantity":1,"unit_price":89.99,"item_type":"service"},
            {"description":"Glass Screen Protector","quantity":2,"unit_price":14.99,"item_type":"product"}
        ]"#;
        create_recurring_invoice_rule(
            &ctx,
            "t_1".into(),
            "cust_1".into(),
            "With Items".into(),
            "weekly".into(),
            1,
            14,
            items_json.into(),
            1000, // past timestamp
        );

        generate_recurring_invoices(&ctx, "t_1".into());

        // Invoice should have been created
        use crate::invoice::{invoice_line_items, invoices};
        let all_invoices: Vec<crate::invoice::Invoice> = ctx.db.invoices().iter().collect();
        assert_eq!(all_invoices.len(), 1, "should have created one invoice");

        // Line items should have been created
        let line_items: Vec<crate::invoice::InvoiceLineItem> =
            ctx.db.invoice_line_items().iter().collect();
        assert_eq!(line_items.len(), 2, "should have created 2 line items");

        // Verify line item details
        let item1 = &line_items[0];
        assert_eq!(item1.description, "Screen Repair");
        assert_eq!(item1.quantity, 1.0);
        assert_eq!(item1.unit_price, 89.99);
        assert_eq!(item1.total, 89.99);
        assert_eq!(item1.item_type, "service");

        let item2 = &line_items[1];
        assert_eq!(item2.description, "Glass Screen Protector");
        assert_eq!(item2.quantity, 2.0);
        assert_eq!(item2.unit_price, 14.99);
        assert_eq!(item2.total, 29.98);
        assert_eq!(item2.item_type, "product");

        // Verify invoice totals were recalculated
        let inv = &all_invoices[0];
        assert!(
            (inv.subtotal - 119.97).abs() < 0.001,
            "subtotal should be sum of line item totals"
        );
        assert!(inv.total > 0.0);
    }

    #[test]
    fn test_delete_nonexistent() {
        let ctx = test_ctx();
        // Deleting a non-existent id should not panic
        delete_recurring_invoice_rule(&ctx, "rir_nonexistent".into(), "t_1".into());
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 0);
    }

    #[test]
    fn test_update_rule_cross_tenant_isolation() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(
            &ctx,
            "t_1".into(),
            "cust_1".into(),
            "Original".into(),
            "weekly".into(),
            1,
            14,
            String::new(),
            1700000000000,
        );
        let id = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .next()
            .expect("expected rule to exist")
            .id
            .clone();

        // A different tenant tries to update the rule — must be a no-op.
        update_recurring_invoice_rule(
            &ctx,
            id.clone(),
            "t_2".into(),
            "Hijacked".into(),
            "daily".into(),
            1,
            0,
            String::new(),
            1,
            "cancelled".into(),
        );

        let rule = ctx
            .db
            .recurring_invoice_rules()
            .id()
            .find(&id)
            .expect("expected rule to exist");
        assert_eq!(rule.name, "Original", "cross-tenant update must not apply");
        assert_eq!(rule.frequency, "weekly");
        assert_eq!(rule.status, "active");
    }

    #[test]
    fn test_delete_rule_cross_tenant_isolation() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(
            &ctx,
            "t_1".into(),
            "cust_1".into(),
            "Keep Me".into(),
            "daily".into(),
            1,
            0,
            String::new(),
            1700000000000,
        );
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 1);
        let id = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .next()
            .expect("expected rule to exist")
            .id
            .clone();

        // A different tenant tries to delete — must be a no-op.
        delete_recurring_invoice_rule(&ctx, id.clone(), "t_2".into());
        assert_eq!(
            ctx.db.recurring_invoice_rules().iter().count(),
            1,
            "cross-tenant delete must not remove the rule"
        );

        // The owning tenant can still delete it.
        delete_recurring_invoice_rule(&ctx, id, "t_1".into());
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 0);
    }

    #[test]
    fn test_generate_invoices_tenant_isolation() {
        let ctx = test_ctx();
        // Two tenants, both with a due rule.
        create_recurring_invoice_rule(
            &ctx,
            "t_1".into(),
            "cust_1".into(),
            "T1 Due".into(),
            "monthly".into(),
            1,
            30,
            String::new(),
            1000, // past timestamp
        );
        create_recurring_invoice_rule(
            &ctx,
            "t_2".into(),
            "cust_2".into(),
            "T2 Due".into(),
            "monthly".into(),
            1,
            30,
            String::new(),
            1000, // past timestamp
        );
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 2);

        // Generate for tenant t_1 only.
        generate_recurring_invoices(&ctx, "t_1".into());

        use crate::invoice::{invoices, Invoice};
        let invoices: Vec<Invoice> = ctx.db.invoices().iter().collect();
        assert_eq!(invoices.len(), 1, "only t_1's rule should generate");
        assert_eq!(invoices[0].tenant_id, "t_1");

        // t_2's rule must still be due (untouched).
        let t2_rule = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .find(|r| r.tenant_id == "t_2")
            .expect("expected t_2 rule");
        assert_eq!(t2_rule.last_generated_date, 0, "t_2 rule must be untouched");
    }
}
