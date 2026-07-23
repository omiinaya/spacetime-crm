use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_save_payment_method() {
        let ctx = test_ctx();
        save_payment_method(&ctx, "t_pm".into(), "cust_1".into(),
            "pm_stripe_123".into(), "Visa".into(), "4242".into(), 12, 2028);
        let methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter().collect();
        assert_eq!(methods.len(), 1);
        let m = &methods[0];
        assert!(m.id.starts_with("pm_"));
        assert_eq!(m.brand, "Visa");
        assert_eq!(m.last4, "4242");
        assert!(m.is_default); // First method = default
    }

    #[test]
    fn test_set_default_payment_method() {
        let ctx = test_ctx();
        save_payment_method(&ctx, "t".into(), "cust_1".into(), "pm_s1".into(), "Visa".into(), "1111".into(), 1, 2025);
        save_payment_method(&ctx, "t".into(), "cust_1".into(), "pm_s2".into(), "MC".into(), "2222".into(), 2, 2026);
        let methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter().collect();
        assert_eq!(methods.len(), 2);
        // First method was default, now set second as default
        let second = methods.iter().find(|m| m.last4 == "2222").expect("expected payment method with last4 2222");
        set_default_payment_method(&ctx, second.id.clone(), "cust_1".into());
        let updated_methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter().collect();
        let first = updated_methods.iter().find(|m| m.last4 == "1111").expect("expected payment method with last4 1111");
        let second2 = updated_methods.iter().find(|m| m.last4 == "2222").expect("expected payment method with last4 2222");
        assert!(!first.is_default);
        assert!(second2.is_default);
    }

    #[test]
    fn test_delete_payment_method() {
        let ctx = test_ctx();
        save_payment_method(&ctx, "t".into(), "c1".into(), "pm_d".into(), "V".into(), "0000".into(), 1, 2025);
        assert_eq!(ctx.db.saved_payment_methods().iter().count(), 1);
        let id = ctx.db.saved_payment_methods().iter().next().expect("expected at least one saved_payment_methods record").id.clone();
        delete_payment_method(&ctx, id);
        assert_eq!(ctx.db.saved_payment_methods().iter().count(), 0);
    }
}
