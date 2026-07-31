#[cfg(test)]
mod tests {
    use crate::payment::payment;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
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
        )
        .unwrap();
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
        )
        .unwrap();
        assert_eq!(ctx.db.payment().iter().count(), 1);
        let id = ctx.db.payment().iter().next().unwrap().id.clone();
        delete_payment(&ctx, id);
        assert_eq!(ctx.db.payment().iter().count(), 0);
    }

    #[test]
    fn test_payment_multiple_currencies() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t_1".into(),
            "inv_1".into(),
            "c_1".into(),
            100.0,
            "cash".into(),
            "".into(),
            "".into(),
            "USD".into(),
        )
        .unwrap();
        record_payment(
            &ctx,
            "t_1".into(),
            "inv_2".into(),
            "c_1".into(),
            200.0,
            "wire".into(),
            "".into(),
            "".into(),
            "EUR".into(),
        )
        .unwrap();
        assert_eq!(ctx.db.payment().iter().count(), 2);
        let eur: Vec<Payment> = ctx
            .db
            .payment()
            .iter()
            .filter(|p| p.currency == "EUR")
            .collect();
        assert_eq!(eur.len(), 1);
    }

    #[test]
    fn test_delete_nonexistent_payment() {
        let ctx = test_ctx();
        delete_payment(&ctx, "pmt_nonexistent".into());
        assert_eq!(ctx.db.payment().iter().count(), 0);
    }

    // ─── Multi-currency consistency ─────────────────────────────

    fn create_invoice_with_currency(ctx: &ReducerContext, currency: &str) -> String {
        create_invoice(
            ctx,
            "t_1".into(),
            "cust_1".into(),
            "".into(),
            "".into(),
            "".into(),
            0,
            currency.into(),
        )
        .unwrap();
        ctx.db
            .invoices()
            .iter()
            .next()
            .expect("expected an invoices record")
            .id
            .clone()
    }

    #[test]
    fn test_payment_currency_mismatch_rejected() {
        let ctx = test_ctx();
        let inv_id = create_invoice_with_currency(&ctx, "EUR");
        let err = record_payment(
            &ctx,
            "t_1".into(),
            inv_id,
            "cust_1".into(),
            100.0,
            "cash".into(),
            "".into(),
            "".into(),
            "USD".into(),
        )
        .unwrap_err();
        assert!(
            err.contains("Currency mismatch") && err.contains("EUR") && err.contains("USD"),
            "unexpected error: {err}"
        );
        assert_eq!(
            ctx.db.payment().iter().count(),
            0,
            "mismatched payment must not be stored"
        );
    }

    #[test]
    fn test_payment_matching_currency_accepted() {
        let ctx = test_ctx();
        let inv_id = create_invoice_with_currency(&ctx, "EUR");
        record_payment(
            &ctx,
            "t_1".into(),
            inv_id,
            "cust_1".into(),
            100.0,
            "cash".into(),
            "".into(),
            "".into(),
            "EUR".into(),
        )
        .unwrap();
        assert_eq!(ctx.db.payment().iter().count(), 1);
    }

    #[test]
    fn test_payment_without_invoice_allowed() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t_1".into(),
            "".into(),
            "cust_1".into(),
            100.0,
            "cash".into(),
            "".into(),
            "".into(),
            "USD".into(),
        )
        .unwrap();
        assert_eq!(ctx.db.payment().iter().count(), 1);
    }

    #[test]
    fn test_payment_unsupported_currency_rejected() {
        let ctx = test_ctx();
        let err = record_payment(
            &ctx,
            "t_1".into(),
            "".into(),
            "cust_1".into(),
            100.0,
            "cash".into(),
            "".into(),
            "".into(),
            "JPY".into(),
        )
        .unwrap_err();
        assert!(
            err.contains("Unsupported currency"),
            "unexpected error: {err}"
        );
        assert_eq!(ctx.db.payment().iter().count(), 0);
    }

    #[test]
    fn test_payment_lowercase_currency_rejected() {
        let ctx = test_ctx();
        let err = record_payment(
            &ctx,
            "t_1".into(),
            "".into(),
            "cust_1".into(),
            100.0,
            "cash".into(),
            "".into(),
            "".into(),
            "usd".into(),
        )
        .unwrap_err();
        assert!(
            err.contains("Unsupported currency"),
            "unexpected error: {err}"
        );
        assert_eq!(ctx.db.payment().iter().count(), 0);
    }
}
