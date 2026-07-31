use spacetimedb::*;

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

#[spacetimedb::reducer]
pub fn create_estimate(
    ctx: &ReducerContext,
    tenant_id: String,
    customer_id: String,
    ticket_id: String,
    notes: String,
    expires_at: u64,
    currency: String,
) -> Result<(), String> {
    super::currency::validate_currency(&currency)?;
    let id = super::make_id("est", ctx);
    let now = super::now_ms(ctx);
    let estimate_number = ctx.db.estimates().iter().count() as u64 + 1001;
    ctx.db.estimates().insert(Estimate {
        id,
        tenant_id,
        customer_id,
        ticket_id,
        estimate_number,
        status: "draft".to_string(),
        subtotal: 0.0,
        tax_rate: 0.0,
        tax_amount: 0.0,
        total: 0.0,
        discount_amount: 0.0,
        notes,
        expires_at,
        invoice_id: String::new(),
        currency,
        created_at: now,
        updated_at: now,
    });
    Ok(())
}

#[spacetimedb::reducer]
pub fn update_estimate_status(ctx: &ReducerContext, id: String, status: String) {
    if let Some(e) = ctx.db.estimates().id().find(&id) {
        ctx.db.estimates().id().update(Estimate { status, ..e });
    }
}

#[spacetimedb::reducer]
pub fn add_estimate_line_item(
    ctx: &ReducerContext,
    estimate_id: String,
    item_type: String,
    description: String,
    quantity: f64,
    unit_price: f64,
) {
    let id = super::make_id("eln", ctx);
    let total = quantity * unit_price;
    let sort = ctx
        .db
        .estimate_line_items()
        .iter()
        .filter(|i| i.estimate_id == estimate_id)
        .count() as u32;
    let tenant_id = ctx
        .db
        .estimates()
        .id()
        .find(&estimate_id)
        .map_or(String::new(), |est| est.tenant_id.clone());
    ctx.db.estimate_line_items().insert(EstimateLineItem {
        id,
        tenant_id,
        estimate_id: estimate_id.clone(),
        item_type,
        description,
        quantity,
        unit_price,
        total,
        sort_order: sort,
    });
    if let Some(est) = ctx.db.estimates().id().find(&estimate_id) {
        let items: Vec<EstimateLineItem> = ctx
            .db
            .estimate_line_items()
            .iter()
            .filter(|i| i.estimate_id == estimate_id)
            .collect();
        let subtotal: f64 = items.iter().map(|i| i.total).sum();
        let tax_amount = subtotal * est.tax_rate / 100.0;
        ctx.db.estimates().id().update(Estimate {
            subtotal,
            tax_amount,
            total: subtotal + tax_amount - est.discount_amount,
            updated_at: super::now_ms(ctx),
            ..est
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_estimate(ctx: &ReducerContext, id: String) {
    ctx.db.estimates().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn convert_estimate_to_invoice(ctx: &ReducerContext, estimate_id: String) {
    use crate::invoice::*;

    if let Some(est) = ctx.db.estimates().id().find(&estimate_id) {
        let now = super::now_ms(ctx);
        // Create invoice from estimate
        let inv_id = super::make_id("inv", ctx);
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
            currency: est.currency.clone(),
            created_at: now,
            updated_at: now,
        });
        // Copy line items with unique IDs (add counter to avoid same-tick collision)
        for (li_idx, item) in ctx
            .db
            .estimate_line_items()
            .iter()
            .filter(|i| i.estimate_id == estimate_id)
            .enumerate()
        {
            let li_id = format!(
                "iln_{}_{}_{}",
                now,
                li_idx,
                ctx.sender().to_hex().chars().take(8).collect::<String>()
            );
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

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;
    use crate::invoice::{invoice_line_items, invoices, InvoiceLineItem};

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_create_estimate() {
        let ctx = test_ctx();
        create_estimate(
            &ctx,
            "t_est".into(),
            "cust_1".into(),
            "tkt_1".into(),
            "Estimate notes".into(),
            1700500000000,
            "USD".into(),
        )
        .unwrap();
        let estimates: Vec<Estimate> = ctx.db.estimates().iter().collect();
        assert_eq!(estimates.len(), 1);
        let e = &estimates[0];
        assert!(e.id.starts_with("est_"));
        assert_eq!(e.status, "draft");
        assert_eq!(e.estimate_number, 1001);
        assert_eq!(e.customer_id, "cust_1");
        assert_eq!(e.ticket_id, "tkt_1");
        assert_eq!(e.notes, "Estimate notes");
        assert_eq!(e.currency, "USD");
    }

    #[test]
    fn test_update_estimate_status() {
        let ctx = test_ctx();
        create_estimate(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        )
        .unwrap();
        let id = ctx
            .db
            .estimates()
            .iter()
            .next()
            .expect("expected at least one estimates record")
            .id
            .clone();
        assert_eq!(
            ctx.db
                .estimates()
                .id()
                .find(&id)
                .expect("expected record to exist")
                .status,
            "draft"
        );
        update_estimate_status(&ctx, id.clone(), "approved".into());
        assert_eq!(
            ctx.db
                .estimates()
                .id()
                .find(&id)
                .expect("expected record to exist")
                .status,
            "approved"
        );
    }

    #[test]
    fn test_add_estimate_line_item() {
        let ctx = test_ctx();
        create_estimate(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        )
        .unwrap();
        let est_id = ctx
            .db
            .estimates()
            .iter()
            .next()
            .expect("expected at least one estimates record")
            .id
            .clone();
        add_estimate_line_item(
            &ctx,
            est_id.clone(),
            "part".into(),
            "Screen".into(),
            1.0,
            89.99,
        );
        let items: Vec<EstimateLineItem> = ctx.db.estimate_line_items().iter().collect();
        assert_eq!(items.len(), 1);
        let item = &items[0];
        assert!(item.id.starts_with("eln_"));
        assert!((item.total - 89.99).abs() < 0.01);

        // Verify estimate totals were recalculated
        let est = ctx
            .db
            .estimates()
            .id()
            .find(&est_id)
            .expect("expected record to exist");
        assert!((est.subtotal - 89.99).abs() < 0.01);
        assert!((est.total - 89.99).abs() < 0.01);
    }

    #[test]
    fn test_delete_estimate() {
        let ctx = test_ctx();
        create_estimate(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        )
        .unwrap();
        assert_eq!(ctx.db.estimates().iter().count(), 1);
        let id = ctx
            .db
            .estimates()
            .iter()
            .next()
            .expect("expected at least one estimates record")
            .id
            .clone();
        delete_estimate(&ctx, id);
        assert_eq!(ctx.db.estimates().iter().count(), 0);
    }

    #[test]
    fn test_convert_estimate_to_invoice() {
        let ctx = test_ctx();
        create_estimate(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "Convert me".into(),
            1000,
            "USD".into(),
        )
        .unwrap();
        let est_id = ctx
            .db
            .estimates()
            .iter()
            .next()
            .expect("expected at least one estimates record")
            .id
            .clone();
        // Add line items
        add_estimate_line_item(
            &ctx,
            est_id.clone(),
            "service".into(),
            "Repair".into(),
            1.0,
            200.0,
        );
        add_estimate_line_item(
            &ctx,
            est_id.clone(),
            "part".into(),
            "Part".into(),
            2.0,
            25.0,
        );

        assert_eq!(ctx.db.estimates().iter().count(), 1);
        assert_eq!(ctx.db.invoices().iter().count(), 0);
        assert_eq!(ctx.db.estimate_line_items().iter().count(), 2);

        convert_estimate_to_invoice(&ctx, est_id.clone());

        // Estimate should be approved with invoice_id set
        let est = ctx
            .db
            .estimates()
            .id()
            .find(&est_id)
            .expect("expected record to exist");
        assert_eq!(est.status, "approved");
        assert!(!est.invoice_id.is_empty());

        // Invoice should exist with correct fields
        assert_eq!(ctx.db.invoices().iter().count(), 1);
        let inv = ctx
            .db
            .invoices()
            .iter()
            .next()
            .expect("expected at least one invoices record");
        assert_eq!(inv.customer_id, "c1");
        assert_eq!(inv.status, "draft");
        assert!((inv.subtotal - 250.0).abs() < 0.01);

        // Line items should be copied
        assert_eq!(ctx.db.invoice_line_items().iter().count(), 2);
        let copied: Vec<InvoiceLineItem> = ctx
            .db
            .invoice_line_items()
            .iter()
            .filter(|i| i.invoice_id == inv.id)
            .collect();
        assert_eq!(copied.len(), 2);
    }

    #[test]
    fn test_delete_nonexistent_estimate() {
        let ctx = test_ctx();
        // Deleting a non-existent estimate should not panic
        delete_estimate(&ctx, "est_nonexistent".into());
        assert_eq!(ctx.db.estimates().iter().count(), 0);
    }

    #[test]
    fn test_update_status_nonexistent() {
        let ctx = test_ctx();
        // Updating status on a non-existent estimate should not panic
        update_estimate_status(&ctx, "est_fake".into(), "approved".into());
        assert_eq!(ctx.db.estimates().iter().count(), 0);
    }

    #[test]
    fn test_add_line_item_nonexistent_estimate() {
        let ctx = test_ctx();
        // Adding line item to a non-existent estimate should not panic
        add_estimate_line_item(
            &ctx,
            "est_nonexistent".into(),
            "part".into(),
            "Widget".into(),
            1.0,
            10.0,
        );
        // Line item is still inserted but totals won't be recalculated
        let items: Vec<EstimateLineItem> = ctx.db.estimate_line_items().iter().collect();
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].tenant_id, "");
        assert_eq!(ctx.db.estimates().iter().count(), 0);
    }

    #[test]
    fn test_create_estimate_rejects_unsupported_currency() {
        let ctx = test_ctx();
        let err = create_estimate(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "".into(),
            0,
            "JPY".into(),
        )
        .unwrap_err();
        assert!(
            err.contains("Unsupported currency"),
            "unexpected error: {err}"
        );
        assert_eq!(ctx.db.estimates().iter().count(), 0);
    }

    #[test]
    fn test_convert_estimate_preserves_currency() {
        let ctx = test_ctx();
        create_estimate(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "EUR estimate".into(),
            1000,
            "EUR".into(),
        )
        .unwrap();
        let est_id = ctx
            .db
            .estimates()
            .iter()
            .next()
            .expect("expected at least one estimates record")
            .id
            .clone();
        convert_estimate_to_invoice(&ctx, est_id);
        let inv = ctx
            .db
            .invoices()
            .iter()
            .next()
            .expect("expected the converted invoice");
        assert_eq!(
            inv.currency, "EUR",
            "converted invoice must keep the estimate currency"
        );
    }
}
