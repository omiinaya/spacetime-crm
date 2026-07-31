use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::product::products;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_update_product_quantity() {
        let ctx = test_ctx();
        create_product(
            &ctx,
            "t_pq".into(),
            "Widget".into(),
            "WDG".into(),
            "".into(),
            "".into(),
            "Parts".into(),
            10.0,
            5.0,
            50.0,
            5.0,
            0.0,
            "A1".into(),
        );
        let pid = ctx
            .db
            .products()
            .iter()
            .next()
            .expect("expected at least one products record")
            .id
            .clone();
        assert_eq!(
            ctx.db
                .products()
                .id()
                .find(&pid)
                .expect("expected record to exist")
                .quantity_on_hand,
            50.0
        );
        update_product_quantity(&ctx, pid.clone(), 30.0);
        let updated = ctx
            .db
            .products()
            .id()
            .find(&pid)
            .expect("expected record to exist");
        assert_eq!(updated.quantity_on_hand, 30.0);
        assert_eq!(updated.quantity_available, 30.0);
    }

    #[test]
    fn test_update_nonexistent_product_quantity_doesnt_panic() {
        let ctx = test_ctx();
        update_product_quantity(&ctx, "prod_nope".into(), 99.0);
        assert_eq!(ctx.db.products().iter().count(), 0);
    }

    #[test]
    fn test_import_product() {
        let ctx = test_ctx();
        import_product(
            &ctx,
            "t_ip".into(),
            "prod_imported_1".into(),
            "Imported Widget".into(),
            "IMP-001".into(),
            "123456789".into(),
            "High quality widget".into(),
            "Gadgets".into(),
            29.99,
            12.00,
            100.0,
            10.0,
            5.0,
            0.0,
            "B2".into(),
            true,
            2000000000000,
            2000000000000,
        );
        let products_list: Vec<Product> = ctx.db.products().iter().collect();
        assert_eq!(products_list.len(), 1);
        let p = &products_list[0];
        assert_eq!(p.id, "prod_imported_1");
        assert_eq!(p.name, "Imported Widget");
        assert_eq!(p.price, 29.99);
        assert_eq!(p.quantity_on_hand, 100.0);
        assert_eq!(p.quantity_committed, 10.0);
        assert_eq!(p.quantity_available, 90.0);
        assert_eq!(p.created_at, 2000000000000);
    }
}
