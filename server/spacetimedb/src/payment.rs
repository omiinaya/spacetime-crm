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
) -> Result<(), String> {
    super::currency::validate_currency(&currency)?;
    super::currency::ensure_payment_matches_invoice(ctx, &invoice_id, &currency)?;
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
    Ok(())
}

#[spacetimedb::reducer]
pub fn delete_payment(ctx: &ReducerContext, id: String) {
    ctx.db.payment().id().delete(&id);
}

#[cfg(test)]
mod payment_tests {
    use super::*;

    #[test]
    fn test_payment_basic() {
        // TODO: implement basic test
        assert!(true);
    }
}
