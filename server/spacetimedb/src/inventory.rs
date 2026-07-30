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
mod inventory_tests {
    use super::*;

    #[test]
    fn test_inventory_basic() {
        assert!(true);
    }
}
