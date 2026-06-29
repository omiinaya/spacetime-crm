use spacetimedb::*;

#[spacetimedb::table(accessor = payment, public)]
#[derive(Debug, Clone)]
pub struct Payment {
    #[primary_key]
    pub id: String,
    pub tenant_id: String,
    pub invoice_id: String,
    pub customer_id: String,
    pub amount: f64,
    pub method: String,
    pub reference: String,
    pub notes: String,
    pub created_at: u64,
}

#[spacetimedb::reducer]
pub fn record_payment(
    ctx: &ReducerContext,
    tenant_id: String,
    invoice_id: String,
    customer_id: String,
    amount: f64,
    method: String,
    reference: String,
    notes: String,
) {
    let id = super::make_id("pmt", ctx);
    let now = super::now_ms(ctx);
    ctx.db.payment().insert(Payment {
        id,
        tenant_id,
        invoice_id,
        customer_id,
        amount,
        method,
        reference,
        notes,
        created_at: now,
    });
}

#[spacetimedb::reducer]
pub fn delete_payment(ctx: &ReducerContext, id: String) {
    ctx.db.payment().id().delete(&id);
}
