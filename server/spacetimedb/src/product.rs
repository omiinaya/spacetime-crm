// TODO (kanban): Replace 7 unwrap() call(s) with proper error handling
use spacetimedb::*;

#[spacetimedb::table(accessor = products, public)]
#[derive(Debug, Clone)]
pub struct Product {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
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
pub fn create_product(
    ctx: &ReducerContext,
    tenant_id: String,
    name: String,
    sku: String,
    barcode: String,
    description: String,
    category: String,
    price: f64,
    cost: f64,
    quantity_on_hand: f64,
    min_stock: f64,
    location: String,
) {
    let id = super::make_id("prod", ctx);
    let now = super::now_ms(ctx);
    ctx.db.products().insert(Product {
        id,
        tenant_id,
        name,
        sku,
        barcode,
        description,
        category,
        price,
        cost,
        quantity_on_hand,
        quantity_committed: 0.0,
        quantity_available: quantity_on_hand,
        min_stock,
        location,
        active: true,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_product_quantity(ctx: &ReducerContext, id: String, quantity_on_hand: f64) {
    if let Some(p) = ctx.db.products().id().find(&id) {
        let quantity_available = quantity_on_hand - p.quantity_committed;
        ctx.db.products().id().update(Product {
            quantity_on_hand,
            quantity_available,
            updated_at: super::now_ms(ctx),
            ..p
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_product(ctx: &ReducerContext, id: String) {
    ctx.db.products().id().delete(&id);
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_product() {
        let ctx = test_ctx();
        create_product(
            &ctx,
            "t_pr".into(),
            "Screen".into(),
            "SCR-001".into(),
            String::new(),
            String::new(),
            "Parts".into(),
            29.99,
            12.50,
            50.0,
            5.0,
            "A3".into(),
        );
        let products: Vec<Product> = ctx.db.products().iter().collect();
        assert_eq!(products.len(), 1);
        let p = &products[0];
        assert!(p.id.starts_with("prod_"));
        assert_eq!(p.name, "Screen");
        assert_eq!(p.sku, "SCR-001");
        assert_eq!(p.price, 29.99);
        assert_eq!(p.cost, 12.50);
        assert_eq!(p.quantity_on_hand, 50.0);
        assert_eq!(p.quantity_available, 50.0);
        assert_eq!(p.quantity_committed, 0.0);
        assert!(p.active);
        assert_eq!(p.category, "Parts");
        assert_eq!(p.location, "A3");
        assert!(p.created_at > 0);
        assert_eq!(p.created_at, p.updated_at);
    }

    #[test]
    fn test_update_product() {
        let ctx = test_ctx();
        create_product(
            &ctx,
            "t".into(),
            "Old".into(),
            "OLD-001".into(),
            "".into(),
            "".into(),
            "".into(),
            10.0,
            5.0,
            10.0,
            0.0,
            "".into(),
        );
        let p = ctx.db.products().iter().next().unwrap();
        let pid = p.id.clone();
        update_product(
            &ctx,
            pid.clone(),
            "New Name".into(),
            "NEW-001".into(),
            "barcode".into(),
            "desc".into(),
            "cat".into(),
            25.0,
            8.0,
            5.0,
            "B-12".into(),
        );
        let updated = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated.name, "New Name");
        assert_eq!(updated.sku, "NEW-001");
        assert_eq!(updated.price, 25.0);
        assert_eq!(updated.barcode, "barcode");
        assert_eq!(updated.description, "desc");
        assert_eq!(updated.category, "cat");
        assert_eq!(updated.min_stock, 5.0);
        assert_eq!(updated.location, "B-12");
    }

    #[test]
    fn test_update_nonexistent_product() {
        let ctx = test_ctx();
        update_product(
            &ctx,
            "prod_nope".into(),
            "N".into(),
            "N".into(),
            "".into(),
            "".into(),
            "".into(),
            0.0,
            0.0,
            0.0,
            "".into(),
        );
        assert_eq!(ctx.db.products().iter().count(), 0);
    }

    #[test]
    fn test_update_product_quantity() {
        let ctx = test_ctx();
        create_product(
            &ctx,
            "t".into(),
            "W".into(),
            "W".into(),
            "".into(),
            "".into(),
            "".into(),
            10.0,
            5.0,
            50.0,
            5.0,
            "A".into(),
        );
        let pid = ctx.db.products().iter().next().unwrap().id.clone();
        assert_eq!(
            ctx.db.products().id().find(&pid).unwrap().quantity_on_hand,
            50.0
        );
        update_product_quantity(&ctx, pid.clone(), 30.0);
        let updated = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated.quantity_on_hand, 30.0);
        assert_eq!(updated.quantity_available, 30.0);
    }

    #[test]
    fn test_update_product_quantity_nonexistent() {
        let ctx = test_ctx();
        update_product_quantity(&ctx, "prod_nope".into(), 99.0);
        assert_eq!(ctx.db.products().iter().count(), 0);
    }

    #[test]
    fn test_delete_product() {
        let ctx = test_ctx();
        create_product(
            &ctx,
            "t".into(),
            "Del".into(),
            "DEL".into(),
            "".into(),
            "".into(),
            "".into(),
            1.0,
            0.5,
            5.0,
            0.0,
            "".into(),
        );
        assert_eq!(ctx.db.products().iter().count(), 1);
        let id = ctx.db.products().iter().next().unwrap().id.clone();
        delete_product(&ctx, id);
        assert_eq!(ctx.db.products().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_product() {
        let ctx = test_ctx();
        delete_product(&ctx, "prod_nope".into());
        assert_eq!(ctx.db.products().iter().count(), 0);
    }

    #[test]
    fn test_import_product() {
        let ctx = test_ctx();
        import_product(
            &ctx,
            "t".into(),
            "prod_imported_1".into(),
            "Imported Widget".into(),
            "IMP-001".into(),
            "123".into(),
            "High quality".into(),
            "Gadgets".into(),
            29.99,
            12.00,
            100.0,
            10.0,
            5.0,
            "B2".into(),
            true,
            2000000000000,
            2000000000000,
        );
        let p = ctx.db.products().iter().next().unwrap();
        assert_eq!(p.id, "prod_imported_1");
        assert_eq!(p.name, "Imported Widget");
        assert_eq!(p.price, 29.99);
        assert_eq!(p.quantity_on_hand, 100.0);
        assert_eq!(p.quantity_committed, 10.0);
        assert_eq!(p.quantity_available, 90.0);
    }
}

#[spacetimedb::reducer]
pub fn update_product(
    ctx: &ReducerContext,
    id: String,
    name: String,
    sku: String,
    barcode: String,
    description: String,
    category: String,
    price: f64,
    cost: f64,
    min_stock: f64,
    location: String,
) {
    if let Some(p) = ctx.db.products().id().find(&id) {
        ctx.db.products().id().update(Product {
            name,
            sku,
            barcode,
            description,
            category,
            price,
            cost,
            min_stock,
            location,
            updated_at: super::now_ms(ctx),
            ..p
        });
    }
}

#[spacetimedb::reducer]
pub fn import_product(
    ctx: &ReducerContext,
    tenant_id: String,
    id: String,
    name: String,
    sku: String,
    barcode: String,
    description: String,
    category: String,
    price: f64,
    cost: f64,
    quantity_on_hand: f64,
    quantity_committed: f64,
    min_stock: f64,
    location: String,
    active: bool,
    created_at: u64,
    updated_at: u64,
) {
    let quantity_available = quantity_on_hand - quantity_committed;
    ctx.db.products().insert(Product {
        id,
        tenant_id,
        name,
        sku,
        barcode,
        description,
        category,
        price,
        cost,
        quantity_on_hand,
        quantity_committed,
        quantity_available,
        min_stock,
        location,
        active,
        created_at,
        updated_at,
    });
}
