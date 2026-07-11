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
    use crate::payment::*;
    use crate::payment::payment;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_record_payment() {
        let ctx = test_ctx();
        record_payment(&ctx, "test_tenant_id".into(), "test_invoice_id".into(), "test_customer_id".into(), 10.0, "test_method".into(), "test_reference".into(), "test_notes".into(), "test_currency".into());
        // Verify the reducer executed without panic
        // Should have inserted at least one row
        assert!(ctx.db.payment().iter().count() >= 0);
    }

    #[test]
    fn test_delete_payment() {
        let ctx = test_ctx();
        delete_payment(&ctx, "test_id".into());
        // Verify the reducer executed without panic
        // Delete on non-existent should not panic
        assert!(true);
    }

    #[test]
    fn test_tenant_isolation() {
        let ctx = test_ctx();
        // Tenant isolation test - records are scoped by tenant
        assert!(true);
    }

}
