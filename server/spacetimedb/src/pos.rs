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
    let sort = ctx.db.counter_sale_line_item().iter().filter(|i| i.sale_id == sale_id).count() as u32;
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
