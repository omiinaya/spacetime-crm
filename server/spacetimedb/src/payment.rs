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
            "tenant_p".into(),
            "inv_1".into(),
            "cust_1".into(),
            150.00,
            "cash".into(),
            "REF-001".into(),
            "Walk-in payment".into(),
            "USD".into(),
        );
        let payments: Vec<Payment> = ctx.db.payment().iter().collect();
        assert_eq!(payments.len(), 1);
        let p = &payments[0];
        assert!(p.id.starts_with("pmt_"));
        assert_eq!(p.amount, 150.00);
        assert_eq!(p.method, "cash");
        assert_eq!(p.currency, "USD");
        assert_eq!(p.invoice_id, "inv_1");
        assert_eq!(p.customer_id, "cust_1");
        assert_eq!(p.reference, "REF-001");
        assert_eq!(p.notes, "Walk-in payment");
        assert!(p.created_at > 0);
    }

    #[test]
    fn test_record_payment_no_reference() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t".into(),
            "inv_1".into(),
            "c1".into(),
            50.0,
            "card".into(),
            String::new(),
            String::new(),
            "EUR".into(),
        );
        let p = ctx.db.payment().iter().next().unwrap();
        assert_eq!(p.amount, 50.0);
        assert_eq!(p.method, "card");
        assert_eq!(p.currency, "EUR");
    }

    #[test]
    fn test_record_multiple_payments() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t".into(),
            "inv_1".into(),
            "c1".into(),
            50.0,
            "cash".into(),
            "".into(),
            "".into(),
            "USD".into(),
        );
        record_payment(
            &ctx,
            "t".into(),
            "inv_1".into(),
            "c1".into(),
            75.0,
            "card".into(),
            "".into(),
            "".into(),
            "USD".into(),
        );
        record_payment(
            &ctx,
            "t".into(),
            "inv_2".into(),
            "c2".into(),
            200.0,
            "check".into(),
            "CK-001".into(),
            "".into(),
            "USD".into(),
        );
        assert_eq!(ctx.db.payment().iter().count(), 3);
        let total: f64 = ctx.db.payment().iter().map(|p| p.amount).sum();
        assert!((total - 325.0).abs() < 0.01);
    }

    #[test]
    fn test_delete_payment() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t".into(),
            "i".into(),
            "c".into(),
            50.0,
            "cash".into(),
            String::new(),
            String::new(),
            "USD".into(),
        );
        assert_eq!(ctx.db.payment().iter().count(), 1);
        let id = ctx.db.payment().iter().next().unwrap().id.clone();
        delete_payment(&ctx, id);
        assert_eq!(ctx.db.payment().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_payment() {
        let ctx = test_ctx();
        delete_payment(&ctx, "pmt_nonexistent".into());
        assert_eq!(ctx.db.payment().iter().count(), 0);
    }

    #[test]
    fn test_payment_tenant_isolation() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t_a".into(),
            "i1".into(),
            "c1".into(),
            10.0,
            "cash".into(),
            "".into(),
            "".into(),
            "USD".into(),
        );
        record_payment(
            &ctx,
            "t_b".into(),
            "i2".into(),
            "c2".into(),
            20.0,
            "card".into(),
            "".into(),
            "".into(),
            "USD".into(),
        );
        let a_only: Vec<Payment> = ctx
            .db
            .payment()
            .iter()
            .filter(|p| p.tenant_id == "t_a")
            .collect();
        assert_eq!(a_only.len(), 1);
        assert_eq!(a_only[0].amount, 10.0);
    }
}
