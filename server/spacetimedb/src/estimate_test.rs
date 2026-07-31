
#[cfg(test)]
mod tests {
    use crate::*;

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
        );
        let estimates: Vec<Estimate> = ctx.db.estimates().iter().collect();
        assert_eq!(estimates.len(), 1);
        let e = &estimates[0];
        assert!(e.id.starts_with("est_"));
        assert_eq!(e.status, "draft");
        assert_eq!(e.estimate_number, 1001);
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
        );
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
        );
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

        // Verify estimate totals
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
        );
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
        );
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

        // Estimate should be approved
        let est = ctx
            .db
            .estimates()
            .id()
            .find(&est_id)
            .expect("expected record to exist");
        assert_eq!(est.status, "approved");
        assert!(!est.invoice_id.is_empty());

        // Invoice should exist
        assert_eq!(ctx.db.invoices().iter().count(), 1);
        let inv = ctx
            .db
            .invoices()
            .iter()
            .next()
            .expect("expected at least one invoices record");
        assert_eq!(inv.customer_id, "c1");
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
}
