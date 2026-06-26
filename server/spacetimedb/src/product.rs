use spacetimedb::*;

#[spacetimedb::table(accessor = product, public)]
#[derive(Debug, Clone)]
pub struct Product {
    #[primary_key]
    pub id: String,
    pub name: String,
    pub sku: String,
    pub barcode: String,
    pub description: String,
    pub category: String,
    pub price: f64,
    pub cost: f64,
    pub quantity_on_hand: f64,
    pub quantity_committed: f64,
    pub quantity_available: f64,
    pub min_stock: f64,
    pub location: String,
    pub active: bool,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn create_product(ctx: &ReducerContext, name: String, sku: String, description: String, category: String, price: f64, cost: f64, quantity_on_hand: f64) {
    let id = super::make_id("prod", ctx);
    let now = super::now_ms(ctx);
    ctx.db.product().insert(Product {
        id,
        name,
        sku,
        barcode: String::new(),
        description,
        category,
        price,
        cost,
        quantity_on_hand,
        quantity_committed: 0.0,
        quantity_available: quantity_on_hand,
        min_stock: 0.0,
        location: String::new(),
        active: true,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_product_quantity(ctx: &ReducerContext, id: String, quantity_on_hand: f64) {
    if let Some(p) = ctx.db.product().id().find(&id) {
        let quantity_available = quantity_on_hand - p.quantity_committed;
        ctx.db.product().id().update(Product { quantity_on_hand, quantity_available, updated_at: super::now_ms(ctx), ..p });
    }
}

#[spacetimedb::reducer]
pub fn delete_product(ctx: &ReducerContext, id: String) {
    ctx.db.product().id().delete(&id);
}
