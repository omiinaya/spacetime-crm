#[cfg(test)]
mod tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
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
        // Create a past-due sent invoice
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
        ); // due yesterday
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
        mark_overdue_invoices(&ctx); // Should not panic with empty table
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

        // Verify invoice totals recalculated
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
        assert!((inv.tax_amount - 8.875).abs() < 0.001); // 100 * 8.875 / 100
        assert!((inv.total - 108.875).abs() < 0.001);
    }
}
