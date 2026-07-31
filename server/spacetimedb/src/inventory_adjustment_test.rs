
#[cfg(test)]
mod tests {
    use crate::product::products;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_inventory_adjustment() {
        let ctx = test_ctx();
        // Create a product first
        create_product(
            &ctx,
            "t_inv".into(),
            "Battery".into(),
            "BAT-001".into(),
            "".into(),
            "".into(),
            "Parts".into(),
            19.99,
            8.00,
            100.0,
            10.0,
            0.0,
            "A-1".into(),
        );
        let prod = ctx
            .db
            .products()
            .iter()
            .next()
            .expect("expected at least one products record");
        let pid = prod.id.clone();
        assert_eq!(prod.quantity_on_hand, 100.0);

        create_inventory_adjustment(
            &ctx,
            "t_inv".into(),
            pid.clone(),
            -5.0,
            "sold".into(),
            "".into(),
            "Sold 5 units".into(),
            "user_1".into(),
        );
        let adjustments: Vec<InventoryAdjustment> = ctx.db.inventory_adjustment().iter().collect();
        assert_eq!(adjustments.len(), 1);
        let adj = &adjustments[0];
        assert!(adj.id.starts_with("adj_"));
        assert_eq!(adj.quantity_change, -5.0);
        assert_eq!(adj.reason, "sold");

        // Verify product quantity was updated
        let updated = ctx
            .db
            .products()
            .id()
            .find(&pid)
            .expect("expected record to exist");
        assert_eq!(updated.quantity_on_hand, 95.0);
        assert_eq!(updated.quantity_available, 95.0);
    }

    #[test]
    fn test_inventory_adjustment_clamps_to_zero() {
        let ctx = test_ctx();
        create_product(
            &ctx,
            "t".into(),
            "Item".into(),
            "ITM".into(),
            "".into(),
            "".into(),
            "".into(),
            5.0,
            2.0,
            3.0,
            0.0,
            0.0,
            "".into(),
        );
        let pid = ctx
            .db
            .products()
            .iter()
            .next()
            .expect("expected at least one products record")
            .id
            .clone();
        create_inventory_adjustment(
            &ctx,
            "t".into(),
            pid.clone(),
            -10.0,
            "damaged".into(),
            "".into(),
            "".into(),
            "u".into(),
        );
        let updated = ctx
            .db
            .products()
            .id()
            .find(&pid)
            .expect("expected record to exist");
        assert_eq!(updated.quantity_on_hand, 0.0); // clamped to 0
    }

    #[test]
    fn test_delete_inventory_adjustment() {
        let ctx = test_ctx();
        create_product(
            &ctx,
            "t".into(),
            "P".into(),
            "P".into(),
            "".into(),
            "".into(),
            "".into(),
            1.0,
            0.5,
            10.0,
            0.0,
            0.0,
            "".into(),
        );
        let pid = ctx
            .db
            .products()
            .iter()
            .next()
            .expect("expected at least one products record")
            .id
            .clone();
        create_inventory_adjustment(
            &ctx,
            "t".into(),
            pid,
            5.0,
            "received".into(),
            "".into(),
            "".into(),
            "u".into(),
        );
        assert_eq!(ctx.db.inventory_adjustment().iter().count(), 1);
        let id = ctx
            .db
            .inventory_adjustment()
            .iter()
            .next()
            .expect("expected at least one inventory_adjustment record")
            .id
            .clone();
        delete_inventory_adjustment(&ctx, id);
        assert_eq!(ctx.db.inventory_adjustment().iter().count(), 0);
    }
}
