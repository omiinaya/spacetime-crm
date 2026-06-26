use spacetimedb::*;

#[spacetimedb::table(accessor = purchase_order, public)]
#[derive(Debug, Clone)]
pub struct PurchaseOrder {
    #[primary_key]
    pub id: String,
    pub vendor_name: String,
    pub po_number: u64,
    pub status: String,
    pub subtotal: f64,
    pub tax_amount: f64,
    pub shipping_cost: f64,
    pub total: f64,
    pub notes: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::table(accessor = purchase_order_line_item, public)]
#[derive(Debug, Clone)]
pub struct PurchaseOrderLineItem {
    #[primary_key]
    pub id: String,
    pub purchase_order_id: String,
    pub product_id: String,
    pub description: String,
    pub quantity: f64,
    pub unit_price: f64,
    pub total: f64,
    pub received_quantity: f64,
}

#[spacetimedb::reducer]
pub fn create_purchase_order(ctx: &ReducerContext, vendor_name: String, notes: String) {
    let id = super::make_id("po", ctx);
    let now = super::now_ms(ctx);
    let po_number = ctx.db.purchase_order().iter().count() as u64 + 1001;
    ctx.db.purchase_order().insert(PurchaseOrder {
        id,
        vendor_name,
        po_number,
        status: "draft".to_string(),
        subtotal: 0.0,
        tax_amount: 0.0,
        shipping_cost: 0.0,
        total: 0.0,
        notes,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn receive_po_item(ctx: &ReducerContext, id: String, received_quantity: f64) {
    if let Some(item) = ctx.db.purchase_order_line_item().id().find(&id) {
        ctx.db.purchase_order_line_item().id().update(PurchaseOrderLineItem { received_quantity, ..item });
    }
}

#[spacetimedb::reducer]
pub fn delete_purchase_order(ctx: &ReducerContext, id: String) {
    ctx.db.purchase_order().id().delete(&id);
}
