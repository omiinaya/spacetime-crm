// TODO (kanban): Replace 7 unwrap() call(s) with proper error handling
use super::Product as ProductRow;
use crate::product::products;
use spacetimedb::*;

#[spacetimedb::table(accessor = inventory_adjustment, public)]
#[derive(Debug, Clone)]
pub struct InventoryAdjustment {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub product_id: String,
    pub quantity_change: f64,
    pub reason: String, // received, sold, damaged, returned, counted, transferred
    pub reference_id: String, // PO number, ticket number, etc.
    pub notes: String,
    pub user_id: String,
    pub created_at: u64,
}

#[spacetimedb::reducer]
pub fn create_inventory_adjustment(
    ctx: &ReducerContext,
    tenant_id: String,
    product_id: String,
    quantity_change: f64,
    reason: String,
    reference_id: String,
    notes: String,
    user_id: String,
) {
    let id = super::make_id("adj", ctx);
    let now = super::now_ms(ctx);
    ctx.db.inventory_adjustment().insert(InventoryAdjustment {
        id,
        tenant_id,
        product_id: product_id.clone(),
        quantity_change,
        reason,
        reference_id,
        notes,
        user_id,
        created_at: now,
    });
    // Update product quantity
    if let Some(p) = ctx.db.products().id().find(&product_id) {
        let new_qty = (p.quantity_on_hand + quantity_change).max(0.0);
        let quantity_available = new_qty - p.quantity_committed;
        ctx.db.products().id().update(ProductRow {
            quantity_on_hand: new_qty,
            quantity_available,
            updated_at: now,
            ..p
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_inventory_adjustment(ctx: &ReducerContext, id: String) {
    ctx.db.inventory_adjustment().id().delete(&id);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::product::products;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    fn create_test_product(ctx: &ReducerContext) -> String {
        ctx.db.products().insert(crate::Product {
            id: format!("prod_test_{}", ctx.timestamp.to_micros_since_unix_epoch()),
            tenant_id: "t_inv".into(),
            name: "Battery".into(),
            sku: "BAT-001".into(),
            barcode: String::new(),
            description: String::new(),
            category: "Parts".into(),
            price: 19.99,
            cost: 8.00,
            quantity_on_hand: 100.0,
            quantity_committed: 0.0,
            quantity_available: 100.0,
            min_stock: 10.0,
            location: "A-1".into(),
            active: true,
            created_at: 0,
            updated_at: 0,
        });
        ctx.db.products().iter().next().unwrap().id.clone()
    }

    #[test]
    fn test_create_inventory_adjustment() {
        let ctx = test_ctx();
        let pid = create_test_product(&ctx);
        assert_eq!(
            ctx.db.products().id().find(&pid).unwrap().quantity_on_hand,
            100.0
        );

        create_inventory_adjustment(
            &ctx,
            "t_inv".into(),
            pid.clone(),
            -5.0,
            "sold".into(),
            String::new(),
            "Sold 5".into(),
            "user_1".into(),
        );
        let adjustments: Vec<InventoryAdjustment> = ctx.db.inventory_adjustment().iter().collect();
        assert_eq!(adjustments.len(), 1);
        let adj = &adjustments[0];
        assert!(adj.id.starts_with("adj_"));
        assert_eq!(adj.quantity_change, -5.0);
        assert_eq!(adj.reason, "sold");
        assert_eq!(adj.tenant_id, "t_inv");
        assert_eq!(adj.product_id, pid);

        let updated = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated.quantity_on_hand, 95.0);
    }

    #[test]
    fn test_inventory_adjustment_add_stock() {
        let ctx = test_ctx();
        let pid = create_test_product(&ctx);
        create_inventory_adjustment(
            &ctx,
            "t".into(),
            pid.clone(),
            20.0,
            "received".into(),
            "PO-001".into(),
            "New stock".into(),
            "u".into(),
        );
        let updated = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated.quantity_on_hand, 120.0);
    }

    #[test]
    fn test_inventory_adjustment_clamps_to_zero() {
        let ctx = test_ctx();
        let pid = create_test_product(&ctx);
        assert_eq!(
            ctx.db.products().id().find(&pid).unwrap().quantity_on_hand,
            100.0
        );
        create_inventory_adjustment(
            &ctx,
            "t".into(),
            pid.clone(),
            -200.0,
            "damaged".into(),
            String::new(),
            String::new(),
            "u".into(),
        );
        let updated = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated.quantity_on_hand, 0.0);
    }

    #[test]
    fn test_create_inventory_adjustment_no_product() {
        let ctx = test_ctx();
        create_inventory_adjustment(
            &ctx,
            "t".into(),
            "prod_nonexistent".into(),
            10.0,
            "received".into(),
            String::new(),
            String::new(),
            "u".into(),
        );
        let adjustments: Vec<InventoryAdjustment> = ctx.db.inventory_adjustment().iter().collect();
        assert_eq!(adjustments.len(), 1);
    }

    #[test]
    fn test_delete_inventory_adjustment() {
        let ctx = test_ctx();
        let pid = create_test_product(&ctx);
        create_inventory_adjustment(
            &ctx,
            "t".into(),
            pid,
            5.0,
            "received".into(),
            String::new(),
            String::new(),
            "u".into(),
        );
        assert_eq!(ctx.db.inventory_adjustment().iter().count(), 1);
        let id = ctx
            .db
            .inventory_adjustment()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        delete_inventory_adjustment(&ctx, id);
        assert_eq!(ctx.db.inventory_adjustment().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_adjustment() {
        let ctx = test_ctx();
        delete_inventory_adjustment(&ctx, "adj_nonexistent".into());
        assert_eq!(ctx.db.inventory_adjustment().iter().count(), 0);
    }
}
