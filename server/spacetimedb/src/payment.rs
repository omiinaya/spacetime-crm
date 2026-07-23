use spacetimedb::*;

#[spacetimedb::table(accessor = payment, public)]
#[derive(Debug, Clone)]
pub struct Payment {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub invoice_id: String,
    pub customer_id: String,
    pub amount: f64,
    pub method: String,
    pub reference: String,
    pub notes: String,
    pub currency: String,
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
    currency: String,
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
        currency,
        created_at: now,
    });
}

#[spacetimedb::reducer]
pub fn delete_payment(ctx: &ReducerContext, id: String) {
    ctx.db.payment().id().delete(&id);
}

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_record_payment() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t_1".into(),
            "inv_1".into(),
            "cust_1".into(),
            150.00,
            "cash".into(),
            "REF-001".into(),
            "Walk-in".into(),
            "USD".into(),
        );
        let payments: Vec<Payment> = ctx.db.payment().iter().collect();
        assert_eq!(payments.len(), 1);
        let p = &payments[0];
        assert!(p.id.starts_with("pmt_"));
        assert_eq!(p.amount, 150.00);
        assert_eq!(p.method, "cash");
        assert_eq!(p.reference, "REF-001");
        assert_eq!(p.currency, "USD");
    }

    #[test]
    fn test_delete_payment() {
        let ctx = test_ctx();
        record_payment(&ctx, "t_1".into(), "inv_1".into(), "c_1".into(), 50.0, "card".into(), "".into(), "".into(), "USD".into());
        assert_eq!(ctx.db.payment().iter().count(), 1);
        let id = ctx.db.payment().iter().next().unwrap().id.clone();
        delete_payment(&ctx, id);
        assert_eq!(ctx.db.payment().iter().count(), 0);
    }

    #[test]
    fn test_payment_multiple_currencies() {
        let ctx = test_ctx();
        record_payment(&ctx, "t_1".into(), "inv_1".into(), "c_1".into(), 100.0, "cash".into(), "".into(), "".into(), "USD".into());
        record_payment(&ctx, "t_1".into(), "inv_2".into(), "c_1".into(), 200.0, "wire".into(), "".into(), "".into(), "EUR".into());
        assert_eq!(ctx.db.payment().iter().count(), 2);
        let eur: Vec<Payment> = ctx.db.payment().iter().filter(|p| p.currency == "EUR").collect();
        assert_eq!(eur.len(), 1);
    }

    #[test]
    fn test_delete_nonexistent_payment() {
        let ctx = test_ctx();
        delete_payment(&ctx, "pmt_nonexistent".into());
        assert_eq!(ctx.db.payment().iter().count(), 0);
    }
}
