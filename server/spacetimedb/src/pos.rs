// TODO (kanban): Replace 11 unwrap() call(s) with proper error handling
use spacetimedb::*;

#[spacetimedb::table(accessor = counter_sale, public)]
#[derive(Debug, Clone)]
pub struct CounterSale {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub customer_id: String,
    pub customer_name: String,
    pub items_count: u32,
    pub subtotal: f64,
    pub tax_rate: f64,
    pub tax_amount: f64,
    pub discount_amount: f64,
    pub total: f64,
    pub payment_method: String, // cash, card, invoice
    pub amount_tendered: f64,
    pub change_due: f64,
    pub currency: String,
    pub receipt_number: u64,
    pub status: String, // completed, refunded, voided
    pub created_at: u64,
    pub created_by: String,
    pub refunded_at: u64,
}

#[spacetimedb::table(accessor = counter_sale_line_item, public)]
#[derive(Debug, Clone)]
pub struct CounterSaleLineItem {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub sale_id: String,
    pub product_id: String,
    pub product_name: String,
    pub sku: String,
    pub quantity: f64,
    pub unit_price: f64,
    pub total: f64,
    pub sort_order: u32,
}

#[spacetimedb::reducer]
pub fn create_counter_sale(
    ctx: &ReducerContext,
    tenant_id: String,
    customer_id: String,
    customer_name: String,
    payment_method: String,
    amount_tendered: f64,
    tax_rate: f64,
    discount_amount: f64,
    currency: String,
) {
    let id = super::make_id("pos", ctx);
    let now = super::now_ms(ctx);
    let receipt_number = ctx.db.counter_sale().iter().count() as u64 + 1001;
    ctx.db.counter_sale().insert(CounterSale {
        id: id.clone(),
        tenant_id,
        customer_id,
        customer_name,
        items_count: 0,
        subtotal: 0.0,
        tax_rate,
        tax_amount: 0.0,
        discount_amount,
        total: 0.0,
        payment_method,
        amount_tendered,
        change_due: 0.0,
        currency,
        receipt_number,
        status: "completed".to_string(),
        created_at: now,
        created_by: String::new(),
        refunded_at: 0,
    });
}

#[spacetimedb::reducer]
pub fn add_counter_sale_item(
    ctx: &ReducerContext,
    tenant_id: String,
    sale_id: String,
    product_id: String,
    product_name: String,
    sku: String,
    quantity: f64,
    unit_price: f64,
) {
    let id = super::make_id("psl", ctx);
    let total = quantity * unit_price;
    let sort = ctx
        .db
        .counter_sale_line_item()
        .iter()
        .filter(|i| i.sale_id == sale_id)
        .count() as u32;
    ctx.db.counter_sale_line_item().insert(CounterSaleLineItem {
        id,
        tenant_id,
        sale_id: sale_id.clone(),
        product_id,
        product_name,
        sku,
        quantity,
        unit_price,
        total,
        sort_order: sort,
    });

    // Recalc sale totals
    if let Some(sale) = ctx.db.counter_sale().id().find(&sale_id) {
        let items: Vec<CounterSaleLineItem> = ctx
            .db
            .counter_sale_line_item()
            .iter()
            .filter(|i| i.sale_id == sale_id)
            .collect();
        let items_count = items.len() as u32;
        let subtotal: f64 = items.iter().map(|i| i.total).sum();
        let tax_amount = subtotal * sale.tax_rate / 100.0;
        let total = subtotal + tax_amount - sale.discount_amount;
        let change_due = if sale.amount_tendered > total {
            sale.amount_tendered - total
        } else {
            0.0
        };
        ctx.db.counter_sale().id().update(CounterSale {
            items_count,
            subtotal,
            tax_amount,
            total,
            change_due,
            ..sale
        });
    }
}

#[spacetimedb::reducer]
pub fn refund_counter_sale(ctx: &ReducerContext, id: String) {
    let now = super::now_ms(ctx);
    if let Some(sale) = ctx.db.counter_sale().id().find(&id) {
        ctx.db.counter_sale().id().update(CounterSale {
            status: "refunded".to_string(),
            refunded_at: now,
            ..sale
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_counter_sale(ctx: &ReducerContext, id: String) {
    // Delete line items first
    let items: Vec<CounterSaleLineItem> = ctx
        .db
        .counter_sale_line_item()
        .iter()
        .filter(|i| i.sale_id == id)
        .collect();
    for item in &items {
        ctx.db.counter_sale_line_item().id().delete(&item.id);
    }
    ctx.db.counter_sale().id().delete(&id);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::product::products;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
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
        );
        let sales: Vec<CounterSale> = ctx.db.counter_sale().iter().collect();
        assert_eq!(sales.len(), 1);
        let s = &sales[0];
        assert!(s.id.starts_with("pos_"));
        assert_eq!(s.tenant_id, "t_pos");
        assert_eq!(s.customer_name, "Walk-in");
        assert_eq!(s.payment_method, "cash");
        assert_eq!(s.status, "completed");
        assert_eq!(s.receipt_number, 1001);
        assert_eq!(s.currency, "USD");
        assert!((s.amount_tendered - 100.0).abs() < 0.01);
        assert!((s.tax_rate - 8.0).abs() < 0.01);
        assert!(s.created_at > 0);
    }

    #[test]
    fn test_create_counter_sale_with_discount() {
        let ctx = test_ctx();
        create_counter_sale(
            &ctx,
            "t".into(),
            String::new(),
            String::new(),
            "card".into(),
            50.0,
            0.0,
            5.0,
            "USD".into(),
        );
        let s = ctx.db.counter_sale().iter().next().unwrap();
        assert!((s.discount_amount - 5.0).abs() < 0.01);
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
        );
        let sale_id = ctx.db.counter_sale().iter().next().unwrap().id.clone();

        // Create product
        ctx.db.products().insert(crate::Product {
            id: "prod_pos_test".into(),
            tenant_id: "t".into(),
            name: "Cable".into(),
            sku: "CBL".into(),
            barcode: String::new(),
            description: String::new(),
            category: "Acc".into(),
            price: 9.99,
            cost: 4.0,
            quantity_on_hand: 20.0,
            quantity_committed: 0.0,
            quantity_available: 20.0,
            min_stock: 0.0,
            location: String::new(),
            active: true,
            created_at: 0,
            updated_at: 0,
        });
        let prod_id = ctx.db.products().iter().next().unwrap().id.clone();

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
        assert_eq!(ctx.db.counter_sale_line_item().iter().count(), 1);
        let item = ctx.db.counter_sale_line_item().iter().next().unwrap();
        assert!(item.id.starts_with("psl_"));
        assert_eq!(item.product_name, "Cable");
        assert_eq!(item.quantity, 2.0);
        assert!((item.total - 19.98).abs() < 0.01);

        // Verify sale recalculated
        let sale = ctx.db.counter_sale().id().find(&sale_id).unwrap();
        assert_eq!(sale.items_count, 1);
        assert!((sale.subtotal - 19.98).abs() < 0.01);
    }

    #[test]
    fn test_add_multiple_counter_sale_items() {
        let ctx = test_ctx();
        create_counter_sale(
            &ctx,
            "t".into(),
            "c1".into(),
            String::new(),
            "card".into(),
            100.0,
            0.0,
            0.0,
            "USD".into(),
        );
        let sale_id = ctx.db.counter_sale().iter().next().unwrap().id.clone();
        add_counter_sale_item(
            &ctx,
            "t".into(),
            sale_id.clone(),
            String::new(),
            "Item A".into(),
            String::new(),
            1.0,
            10.0,
        );
        add_counter_sale_item(
            &ctx,
            "t".into(),
            sale_id.clone(),
            String::new(),
            "Item B".into(),
            String::new(),
            2.0,
            5.0,
        );
        assert_eq!(ctx.db.counter_sale_line_item().iter().count(), 2);
        let sale = ctx.db.counter_sale().id().find(&sale_id).unwrap();
        assert_eq!(sale.items_count, 2);
        assert!((sale.subtotal - 20.0).abs() < 0.01);
    }

    #[test]
    fn test_refund_counter_sale() {
        let ctx = test_ctx();
        create_counter_sale(
            &ctx,
            "t".into(),
            "c1".into(),
            String::new(),
            "card".into(),
            30.0,
            0.0,
            0.0,
            "USD".into(),
        );
        let sale_id = ctx.db.counter_sale().iter().next().unwrap().id.clone();
        assert_eq!(
            ctx.db.counter_sale().id().find(&sale_id).unwrap().status,
            "completed"
        );
        refund_counter_sale(&ctx, sale_id.clone());
        let refunded = ctx.db.counter_sale().id().find(&sale_id).unwrap();
        assert_eq!(refunded.status, "refunded");
        assert!(refunded.refunded_at > 0);
    }

    #[test]
    fn test_refund_nonexistent_sale() {
        let ctx = test_ctx();
        refund_counter_sale(&ctx, "pos_nope".into());
        assert_eq!(ctx.db.counter_sale().iter().count(), 0);
    }

    #[test]
    fn test_delete_counter_sale() {
        let ctx = test_ctx();
        create_counter_sale(
            &ctx,
            "t".into(),
            "c1".into(),
            String::new(),
            "cash".into(),
            10.0,
            0.0,
            0.0,
            "USD".into(),
        );
        let sale_id = ctx.db.counter_sale().iter().next().unwrap().id.clone();
        add_counter_sale_item(
            &ctx,
            "t".into(),
            sale_id.clone(),
            String::new(),
            "P".into(),
            String::new(),
            1.0,
            5.0,
        );
        assert_eq!(ctx.db.counter_sale().iter().count(), 1);
        assert_eq!(ctx.db.counter_sale_line_item().iter().count(), 1);
        delete_counter_sale(&ctx, sale_id);
        assert_eq!(ctx.db.counter_sale().iter().count(), 0);
        assert_eq!(ctx.db.counter_sale_line_item().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_sale() {
        let ctx = test_ctx();
        delete_counter_sale(&ctx, "pos_nope".into());
        assert_eq!(ctx.db.counter_sale().iter().count(), 0);
    }
}
