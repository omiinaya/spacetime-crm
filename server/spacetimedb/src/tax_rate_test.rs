#[cfg(test)]
mod tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_create_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_1".into(), "Sales Tax".into(), 8.25, false);
        let rates: Vec<TaxRate> = ctx.db.tax_rates().iter().collect();
        assert_eq!(rates.len(), 1);
        let r = &rates[0];
        assert!(r.id.starts_with("tax_"));
        assert_eq!(r.name, "Sales Tax");
        assert_eq!(r.rate, 8.25);
        assert!(!r.is_default);
    }

    #[test]
    fn test_create_default_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_1".into(), "Default".into(), 10.0, true);
        create_tax_rate(&ctx, "t_1".into(), "Second".into(), 5.0, true);
        let rates: Vec<TaxRate> = ctx.db.tax_rates().iter().collect();
        // After second is_default=true, first should have is_default=false
        let default_count = rates.iter().filter(|r| r.is_default).count();
        assert_eq!(default_count, 1, "only one tax rate should be default");
        let default = rates
            .iter()
            .find(|r| r.is_default)
            .expect("a default tax rate should exist");
        assert_eq!(default.name, "Second");
    }

    #[test]
    fn test_update_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_1".into(), "Old".into(), 5.0, false);
        let id = ctx
            .db
            .tax_rates()
            .iter()
            .next()
            .expect("expected record")
            .id
            .clone();
        update_tax_rate(&ctx, id.clone(), "Updated".into(), 9.5, true);
        let updated = ctx
            .db
            .tax_rates()
            .id()
            .find(&id)
            .expect("expected to exist");
        assert_eq!(updated.name, "Updated");
        assert_eq!(updated.rate, 9.5);
        assert!(updated.is_default);
    }

    #[test]
    fn test_delete_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_1".into(), "Del".into(), 5.0, false);
        assert_eq!(ctx.db.tax_rates().iter().count(), 1);
        let id = ctx
            .db
            .tax_rates()
            .iter()
            .next()
            .expect("a tax rate should exist")
            .id
            .clone();
        delete_tax_rate(&ctx, id);
        assert_eq!(ctx.db.tax_rates().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_tax_rate() {
        let ctx = test_ctx();
        delete_tax_rate(&ctx, "tax_nonexistent".into());
        assert_eq!(ctx.db.tax_rates().iter().count(), 0);
    }

    #[test]
    fn test_update_nonexistent_tax_rate() {
        let ctx = test_ctx();
        update_tax_rate(&ctx, "tax_nonexistent".into(), "Nope".into(), 5.0, false);
        assert_eq!(ctx.db.tax_rates().iter().count(), 0);
    }
}
