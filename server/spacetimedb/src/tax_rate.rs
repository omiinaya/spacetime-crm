use spacetimedb::*;

#[spacetimedb::table(accessor = tax_rates, public)]
#[derive(Debug, Clone)]
pub struct TaxRate {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub name: String,
    pub rate: f64,
    pub is_default: bool,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn create_tax_rate(
    ctx: &ReducerContext,
    tenant_id: String,
    name: String,
    rate: f64,
    is_default: bool,
) {
    let id = super::make_id("tax", ctx);
    let now = super::now_ms(ctx);
    if is_default {
        for tr in ctx.db.tax_rates().iter() {
            ctx.db.tax_rates().id().update(TaxRate {
                is_default: false,
                ..tr
            });
        }
    }
    ctx.db.tax_rates().insert(TaxRate {
        id,
        tenant_id,
        name,
        rate,
        is_default,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_tax_rate(
    ctx: &ReducerContext,
    id: String,
    name: String,
    rate: f64,
    is_default: bool,
) {
    if let Some(tr) = ctx.db.tax_rates().id().find(&id) {
        let now = super::now_ms(ctx);
        if is_default {
            for tr2 in ctx.db.tax_rates().iter() {
                ctx.db.tax_rates().id().update(TaxRate {
                    is_default: false,
                    ..tr2
                });
            }
        }
        ctx.db.tax_rates().id().update(TaxRate {
            name,
            rate,
            is_default,
            updated_at: now,
            ..tr
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_tax_rate(ctx: &ReducerContext, id: String) {
    ctx.db.tax_rates().id().delete(&id);
}

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
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
        let default = rates.iter().find(|r| r.is_default).unwrap();
        assert_eq!(default.name, "Second");
    }

    #[test]
    fn test_update_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_1".into(), "Old".into(), 5.0, false);
        let id = ctx.db.tax_rates().iter().next().expect("expected record").id.clone();
        update_tax_rate(&ctx, id.clone(), "Updated".into(), 9.5, true);
        let updated = ctx.db.tax_rates().id().find(&id).expect("expected to exist");
        assert_eq!(updated.name, "Updated");
        assert_eq!(updated.rate, 9.5);
        assert!(updated.is_default);
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
