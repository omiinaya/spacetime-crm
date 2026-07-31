use spacetimedb::*;

#[spacetimedb::table(accessor = saved_payment_methods, public)]
#[derive(Debug, Clone)]
pub struct SavedPaymentMethod {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub customer_id: String,
    pub stripe_payment_method_id: String,
    pub brand: String,
    pub last4: String,
    pub exp_month: u32,
    pub exp_year: u32,
    pub is_default: bool,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn save_payment_method(
    ctx: &ReducerContext,
    tenant_id: String,
    customer_id: String,
    stripe_payment_method_id: String,
    brand: String,
    last4: String,
    exp_month: u32,
    exp_year: u32,
) {
    let id = super::make_id("pm", ctx);
    let now = super::now_ms(ctx);
    // Check if this is the first method for this customer — make it default
    let existing = ctx
        .db
        .saved_payment_methods()
        .iter()
        .filter(|m| m.customer_id == customer_id)
        .count();
    ctx.db.saved_payment_methods().insert(SavedPaymentMethod {
        id,
        tenant_id,
        customer_id,
        stripe_payment_method_id,
        brand,
        last4,
        exp_month,
        exp_year,
        is_default: existing == 0,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn set_default_payment_method(ctx: &ReducerContext, id: String, customer_id: String) {
    let now = super::now_ms(ctx);
    // Unset all defaults for this customer
    let methods: Vec<SavedPaymentMethod> = ctx
        .db
        .saved_payment_methods()
        .iter()
        .filter(|m| m.customer_id == customer_id)
        .collect();
    for m in &methods {
        ctx.db
            .saved_payment_methods()
            .id()
            .update(SavedPaymentMethod {
                is_default: m.id == id,
                updated_at: now,
                ..m.clone()
            });
    }
}

#[spacetimedb::reducer]
pub fn delete_payment_method(ctx: &ReducerContext, id: String) {
    ctx.db.saved_payment_methods().id().delete(&id);
}

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_save_first_method() {
        let ctx = test_ctx();
        save_payment_method(
            &ctx,
            "tenant_1".into(),
            "customer_1".into(),
            "pm_abc123".into(),
            "Visa".into(),
            "4242".into(),
            12,
            2028,
        );
        let methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter().collect();
        assert_eq!(methods.len(), 1);
        let m = &methods[0];
        assert!(m.id.starts_with("pm_"));
        assert_eq!(m.customer_id, "customer_1");
        assert_eq!(m.is_default, true);
        assert_eq!(m.brand, "Visa");
        assert_eq!(m.last4, "4242");
    }

    #[test]
    fn test_save_second_method_not_default() {
        let ctx = test_ctx();
        save_payment_method(
            &ctx,
            "tenant_1".into(),
            "customer_1".into(),
            "pm_first".into(),
            "Visa".into(),
            "1111".into(),
            1,
            2026,
        );
        save_payment_method(
            &ctx,
            "tenant_1".into(),
            "customer_1".into(),
            "pm_second".into(),
            "Mastercard".into(),
            "2222".into(),
            5,
            2027,
        );
        let methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter().collect();
        assert_eq!(methods.len(), 2);
        let first = methods
            .iter()
            .find(|m| m.last4 == "1111")
            .expect("first method should be present");
        let second = methods
            .iter()
            .find(|m| m.last4 == "2222")
            .expect("second method should be present");
        assert!(first.is_default, "first method should be default");
        assert!(!second.is_default, "second method should not be default");
    }

    #[test]
    fn test_set_default_payment_method() {
        let ctx = test_ctx();
        save_payment_method(
            &ctx,
            "tenant_1".into(),
            "customer_1".into(),
            "pm_a".into(),
            "Visa".into(),
            "1111".into(),
            1,
            2026,
        );
        save_payment_method(
            &ctx,
            "tenant_1".into(),
            "customer_1".into(),
            "pm_b".into(),
            "Mastercard".into(),
            "2222".into(),
            5,
            2027,
        );
        let second_id = ctx
            .db
            .saved_payment_methods()
            .iter()
            .find(|m| m.last4 == "2222")
            .expect("second payment method pm_b should exist")
            .id
            .clone();
        set_default_payment_method(&ctx, second_id, "customer_1".into());
        let methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter().collect();
        let first = methods
            .iter()
            .find(|m| m.last4 == "1111")
            .expect("first method should still exist");
        let second = methods
            .iter()
            .find(|m| m.last4 == "2222")
            .expect("second method should still exist");
        assert!(
            !first.is_default,
            "first method should no longer be default"
        );
        assert!(second.is_default, "second method should now be default");
    }

    #[test]
    fn test_delete_payment_method() {
        let ctx = test_ctx();
        save_payment_method(
            &ctx,
            "tenant_1".into(),
            "customer_1".into(),
            "pm_to_delete".into(),
            "Visa".into(),
            "0000".into(),
            6,
            2029,
        );
        assert_eq!(ctx.db.saved_payment_methods().iter().count(), 1);
        let id = ctx
            .db
            .saved_payment_methods()
            .iter()
            .next()
            .expect("payment method should exist after being saved")
            .id
            .clone();
        delete_payment_method(&ctx, id);
        assert_eq!(ctx.db.saved_payment_methods().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent() {
        let ctx = test_ctx();
        delete_payment_method(&ctx, "pm_nonexistent".into());
        assert_eq!(ctx.db.saved_payment_methods().iter().count(), 0);
    }
}
