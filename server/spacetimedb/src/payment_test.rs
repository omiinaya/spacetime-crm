use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::payment::payment;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_record_payment() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t_pmt".into(),
            "inv_1".into(),
            "cust_1".into(),
            250.0,
            "credit_card".into(),
            "CH_12345".into(),
            "Online payment".into(),
            "USD".into(),
        );
        let payments: Vec<Payment> = ctx.db.payment().iter().collect();
        assert_eq!(payments.len(), 1);
        let p = &payments[0];
        assert!(p.id.starts_with("pmt_"));
        assert_eq!(p.amount, 250.0);
        assert_eq!(p.method, "credit_card");
        assert_eq!(p.reference, "CH_12345");
        assert_eq!(p.notes, "Online payment");
        assert_eq!(p.currency, "USD");
        assert!(p.created_at > 0);
    }

    #[test]
    fn test_record_payment_different_methods() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t_1".into(),
            "inv_1".into(),
            "c_1".into(),
            50.0,
            "cash".into(),
            "".into(),
            "".into(),
            "USD".into(),
        );
        record_payment(
            &ctx,
            "t_1".into(),
            "inv_2".into(),
            "c_1".into(),
            75.0,
            "check".into(),
            "CK_001".into(),
            "".into(),
            "USD".into(),
        );
        record_payment(
            &ctx,
            "t_1".into(),
            "inv_3".into(),
            "c_1".into(),
            100.0,
            "wire".into(),
            "W_001".into(),
            "".into(),
            "EUR".into(),
        );
        assert_eq!(ctx.db.payment().iter().count(), 3);
    }

    #[test]
    fn test_delete_payment() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t_1".into(),
            "inv_1".into(),
            "c_1".into(),
            50.0,
            "card".into(),
            "".into(),
            "".into(),
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
    fn test_record_payment_negative_amount() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t_1".into(),
            "inv_1".into(),
            "c_1".into(),
            -10.0,
            "refund".into(),
            "".into(),
            "Refund".into(),
            "USD".into(),
        );
        let p = ctx.db.payment().iter().next().expect("expected payment");
        assert!(p.amount < 0.0);
    }
}
