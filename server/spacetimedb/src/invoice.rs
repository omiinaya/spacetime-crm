use spacetimedb::*;

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

#[spacetimedb::reducer]
pub fn create_invoice(
    ctx: &ReducerContext,
    tenant_id: String,
    customer_id: String,
    ticket_id: String,
    notes: String,
    terms: String,
    due_date: u64,
    currency: String,
) {
    let id = super::make_id("inv", ctx);
    let now = super::now_ms(ctx);
    let invoice_number = ctx.db.invoices().iter().count() as u64 + 10001;
    ctx.db.invoices().insert(Invoice {
        id,
        tenant_id,
        customer_id,
        ticket_id,
        invoice_number,
        status: "draft".to_string(),
        subtotal: 0.0,
        tax_rate: 0.0,
        tax_amount: 0.0,
        total: 0.0,
        discount_amount: 0.0,
        discount_percent: 0.0,
        notes,
        terms,
        due_date,
        currency,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_invoice_status(ctx: &ReducerContext, id: String, status: String) {
    if let Some(inv) = ctx.db.invoices().id().find(&id) {
        ctx.db.invoices().id().update(Invoice { status, ..inv });
    }
}

#[spacetimedb::reducer]
pub fn mark_overdue_invoices(ctx: &ReducerContext) {
    let now = super::now_ms(ctx);
    let overdue_targets: Vec<Invoice> = ctx
        .db
        .invoices()
        .iter()
        .filter(|inv| {
            (inv.status == "sent" || inv.status == "partial")
                && inv.due_date > 0
                && inv.due_date < now
        })
        .collect();
    for inv in overdue_targets {
        ctx.db.invoices().id().update(Invoice {
            status: "overdue".to_string(),
            ..inv
        });
    }
}

#[spacetimedb::reducer]
pub fn add_invoice_line_item(
    ctx: &ReducerContext,
    invoice_id: String,
    item_type: String,
    description: String,
    quantity: f64,
    unit_price: f64,
) {
    let id = super::make_id("iln", ctx);
    let total = quantity * unit_price;
    let sort = ctx
        .db
        .invoice_line_items()
        .iter()
        .filter(|i| i.invoice_id == invoice_id)
        .count() as u32;
    // Derive tenant_id from the parent invoice
    let tenant_id = ctx
        .db
        .invoices()
        .id()
        .find(&invoice_id)
        .map_or(String::new(), |inv| inv.tenant_id.clone());
    ctx.db.invoice_line_items().insert(InvoiceLineItem {
        id,
        tenant_id,
        invoice_id: invoice_id.clone(),
        item_type,
        description,
        quantity,
        unit_price,
        total,
        sort_order: sort,
    });
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
            updated_at: super::now_ms(ctx),
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
            updated_at: super::now_ms(ctx),
            ..inv
        });
    }
}

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_invoice() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t_inv".into(),
            "cust_1".into(),
            "tkt_1".into(),
            "Please pay".into(),
            "Net 30".into(),
            1700100000000,
            "USD".into(),
        );
        let invoices: Vec<Invoice> = ctx.db.invoices().iter().collect();
        assert_eq!(invoices.len(), 1);
        let i = &invoices[0];
        assert!(i.id.starts_with("inv_"));
        assert_eq!(i.status, "draft");
        assert_eq!(i.invoice_number, 10001);
        assert_eq!(i.currency, "USD");
    }

    #[test]
    fn test_update_invoice_status() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        );
        let id = ctx
            .db
            .invoices()
            .iter()
            .next()
            .expect("expected at least one invoices record")
            .id
            .clone();
        assert_eq!(
            ctx.db
                .invoices()
                .id()
                .find(&id)
                .expect("expected record to exist")
                .status,
            "draft"
        );
        update_invoice_status(&ctx, id.clone(), "sent".into());
        assert_eq!(
            ctx.db
                .invoices()
                .id()
                .find(&id)
                .expect("expected record to exist")
                .status,
            "sent"
        );
    }

    #[test]
    fn test_mark_overdue_invoices() {
        let ctx = test_ctx();
        let now = ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000;
        create_invoice(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "".into(),
            "".into(),
            now - 86400000,
            "USD".into(),
        );
        let id = ctx
            .db
            .invoices()
            .iter()
            .next()
            .expect("expected at least one invoices record")
            .id
            .clone();
        update_invoice_status(&ctx, id.clone(), "sent".into());
        mark_overdue_invoices(&ctx);
        let updated = ctx
            .db
            .invoices()
            .id()
            .find(&id)
            .expect("expected record to exist");
        assert_eq!(updated.status, "overdue");
    }

    #[test]
    fn test_mark_overdue_no_invoices_doesnt_panic() {
        let ctx = test_ctx();
        mark_overdue_invoices(&ctx);
    }

    #[test]
    fn test_add_invoice_line_item() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        );
        let inv_id = ctx
            .db
            .invoices()
            .iter()
            .next()
            .expect("expected at least one invoices record")
            .id
            .clone();
        add_invoice_line_item(
            &ctx,
            inv_id.clone(),
            "service".into(),
            "Labor".into(),
            2.0,
            75.0,
        );
        let items: Vec<InvoiceLineItem> = ctx.db.invoice_line_items().iter().collect();
        assert_eq!(items.len(), 1);
        let item = &items[0];
        assert!(item.id.starts_with("iln_"));
        assert_eq!(item.description, "Labor");
        assert!((item.total - 150.0).abs() < 0.01);

        let inv = ctx
            .db
            .invoices()
            .id()
            .find(&inv_id)
            .expect("expected record to exist");
        assert!((inv.subtotal - 150.0).abs() < 0.01);
        assert!((inv.total - 150.0).abs() < 0.01);
    }

    #[test]
    fn test_delete_invoice_line_item() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        );
        let inv_id = ctx
            .db
            .invoices()
            .iter()
            .next()
            .expect("expected at least one invoices record")
            .id
            .clone();
        add_invoice_line_item(&ctx, inv_id.clone(), "s".into(), "Item".into(), 1.0, 10.0);
        assert_eq!(ctx.db.invoice_line_items().iter().count(), 1);
        let li_id = ctx
            .db
            .invoice_line_items()
            .iter()
            .next()
            .expect("expected at least one invoice_line_items record")
            .id
            .clone();
        delete_invoice_line_item(&ctx, li_id);
        assert_eq!(ctx.db.invoice_line_items().iter().count(), 0);
    }

    #[test]
    fn test_delete_invoice() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        );
        assert_eq!(ctx.db.invoices().iter().count(), 1);
        let id = ctx
            .db
            .invoices()
            .iter()
            .next()
            .expect("expected at least one invoices record")
            .id
            .clone();
        delete_invoice(&ctx, id);
        assert_eq!(ctx.db.invoices().iter().count(), 0);
    }

    #[test]
    fn test_set_invoice_tax_rate() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        );
        let inv_id = ctx
            .db
            .invoices()
            .iter()
            .next()
            .expect("expected at least one invoices record")
            .id
            .clone();
        add_invoice_line_item(&ctx, inv_id.clone(), "s".into(), "Item".into(), 1.0, 100.0);
        set_invoice_tax_rate(&ctx, inv_id.clone(), 8.875);
        let inv = ctx
            .db
            .invoices()
            .id()
            .find(&inv_id)
            .expect("expected record to exist");
        assert!((inv.tax_rate - 8.875).abs() < 0.001);
        assert!((inv.tax_amount - 8.875).abs() < 0.001);
        assert!((inv.total - 108.875).abs() < 0.001);
    }
}
