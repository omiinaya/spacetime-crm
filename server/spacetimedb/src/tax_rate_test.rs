use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::tax_rate::tax_rates;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_tax".into(), "Sales Tax".into(), 8.25, false);
        let rates: Vec<TaxRate> = ctx.db.tax_rates().iter().collect();
        assert_eq!(rates.len(), 1);
        let r = &rates[0];
        assert!(r.id.starts_with("tax_"));
        assert_eq!(r.name, "Sales Tax");
        assert_eq!(r.rate, 8.25);
        assert!(!r.is_default);
        assert!(r.created_at > 0);
    }

    #[test]
    fn test_create_default_tax_rate_uniqueness() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_1".into(), "Default".into(), 10.0, true);
        create_tax_rate(&ctx, "t_1".into(), "Second".into(), 5.0, true);
        let default_count = ctx
            .db
            .tax_rates()
            .iter()
            .filter(|r: &TaxRate| r.is_default)
            .count();
        assert_eq!(default_count, 1, "only one tax rate should be default");
        let default = ctx.db.tax_rates().iter().find(|r| r.is_default).unwrap();
        assert_eq!(default.name, "Second");
    }

    #[test]
    fn test_create_multiple_non_default() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_1".into(), "State".into(), 5.0, false);
        create_tax_rate(&ctx, "t_1".into(), "City".into(), 2.0, false);
        create_tax_rate(&ctx, "t_1".into(), "Federal".into(), 1.0, false);
        assert_eq!(ctx.db.tax_rates().iter().count(), 3);
        let default_count = ctx
            .db
            .tax_rates()
            .iter()
            .filter(|r: &TaxRate| r.is_default)
            .count();
        assert_eq!(default_count, 0);
    }

    #[test]
    fn test_update_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_1".into(), "Old".into(), 5.0, false);
        let id = ctx.db.tax_rates().iter().next().unwrap().id.clone();
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
    fn test_update_tax_rate_default_clears_others() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_1".into(), "First".into(), 5.0, true);
        create_tax_rate(&ctx, "t_1".into(), "Second".into(), 8.0, false);
        let first_id = ctx
            .db
            .tax_rates()
            .iter()
            .find(|r: &TaxRate| r.name == "First")
            .unwrap()
            .id
            .clone();
        let second_id = ctx
            .db
            .tax_rates()
            .iter()
            .find(|r: &TaxRate| r.name == "Second")
            .unwrap()
            .id
            .clone();
        // Update Second to be default - First should lose default
        update_tax_rate(&ctx, second_id, "Second".into(), 8.0, true);
        let first = ctx.db.tax_rates().id().find(&first_id).unwrap();
        assert!(!first.is_default, "First should no longer be default");
        let default_count = ctx
            .db
            .tax_rates()
            .iter()
            .filter(|r: &TaxRate| r.is_default)
            .count();
        assert_eq!(default_count, 1);
    }

    #[test]
    fn test_delete_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_1".into(), "Del".into(), 5.0, false);
        assert_eq!(ctx.db.tax_rates().iter().count(), 1);
        let id = ctx.db.tax_rates().iter().next().unwrap().id.clone();
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
