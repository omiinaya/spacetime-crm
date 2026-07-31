#[cfg(test)]
mod tests {
    use crate::pos::counter_sale;
    use crate::pos::counter_sale_line_item;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_create_counter_sale() {
        let ctx = test_ctx();
        create_counter_sale(
            &ctx,
            "t_pos".into(),
            "cust_1".into(),
            "Walk-in".into(),
            "cash".into(),
            100.0,
            8.0,
            0.0,
            "USD".into(),
        )
        .unwrap();
        let sales: Vec<CounterSale> = ctx.db.counter_sale().iter().collect();
        assert_eq!(sales.len(), 1);
        let s = &sales[0];
        assert!(s.id.starts_with("pos_"));
        assert_eq!(s.status, "completed");
        assert_eq!(s.receipt_number, 1001);
    }

    #[test]
    fn test_add_counter_sale_item() {
        let ctx = test_ctx();
        create_counter_sale(
            &ctx,
            "t".into(),
            "c1".into(),
            "John".into(),
            "cash".into(),
            50.0,
            8.0,
            0.0,
            "USD".into(),
        )
        .unwrap();
        let sale_id = ctx
            .db
            .counter_sale()
            .iter()
            .next()
            .expect("expected at least one counter_sale record")
            .id
            .clone();
        create_product(
            &ctx,
            "t".into(),
            "Cable".into(),
            "CBL".into(),
            "".into(),
            "".into(),
            "Acc".into(),
            9.99,
            4.0,
            20.0,
            5.0,
            0.0,
            "".into(),
        );
        let prod_id = ctx
            .db
            .products()
            .iter()
            .next()
            .expect("expected at least one products record")
            .id
            .clone();
        add_counter_sale_item(
            &ctx,
            "t".into(),
            sale_id.clone(),
            prod_id,
            "Cable".into(),
            "CBL".into(),
            2.0,
            9.99,
        );

        // Verify line item
        let items: Vec<CounterSaleLineItem> = ctx.db.counter_sale_line_item().iter().collect();
        assert_eq!(items.len(), 1);
        let item = &items[0];
        assert!(item.id.starts_with("psl_"));

        // Verify sale totals were recalculated
        let sale = ctx
            .db
            .counter_sale()
            .id()
            .find(&sale_id)
            .expect("expected record to exist");
        assert_eq!(sale.items_count, 1);
        assert!((sale.subtotal - 19.98).abs() < 0.01);
        assert!(sale.total > 0.0);
    }

    #[test]
    fn test_refund_counter_sale() {
        let ctx = test_ctx();
        create_counter_sale(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "card".into(),
            30.0,
            0.0,
            0.0,
            "USD".into(),
        )
        .unwrap();
        let sale_id = ctx
            .db
            .counter_sale()
            .iter()
            .next()
            .expect("expected at least one counter_sale record")
            .id
            .clone();
        assert_eq!(
            ctx.db
                .counter_sale()
                .id()
                .find(&sale_id)
                .expect("expected record to exist")
                .status,
            "completed"
        );
        refund_counter_sale(&ctx, sale_id.clone());
        let refunded = ctx
            .db
            .counter_sale()
            .id()
            .find(&sale_id)
            .expect("expected record to exist");
        assert_eq!(refunded.status, "refunded");
        assert!(refunded.refunded_at > 0);
    }

    #[test]
    fn test_delete_counter_sale() {
        let ctx = test_ctx();
        create_counter_sale(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "cash".into(),
            10.0,
            0.0,
            0.0,
            "USD".into(),
        )
        .unwrap();
        assert_eq!(ctx.db.counter_sale().iter().count(), 1);
        let id = ctx
            .db
            .counter_sale()
            .iter()
            .next()
            .expect("expected at least one counter_sale record")
            .id
            .clone();
        delete_counter_sale(&ctx, id);
        assert_eq!(ctx.db.counter_sale().iter().count(), 0);
    }

    #[test]
    fn test_create_counter_sale_rejects_unsupported_currency() {
        let ctx = test_ctx();
        let err = create_counter_sale(
            &ctx,
            "t_pos".into(),
            "cust_1".into(),
            "Walk-in".into(),
            "cash".into(),
            100.0,
            8.0,
            0.0,
            "JPY".into(),
        )
        .unwrap_err();
        assert!(
            err.contains("Unsupported currency"),
            "unexpected error: {err}"
        );
        assert_eq!(ctx.db.counter_sale().iter().count(), 0);
    }
}
