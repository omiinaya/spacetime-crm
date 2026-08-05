// TODO (kanban): Replace 10 unwrap() call(s) with proper error handling
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

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_tax".into(), "Sales Tax".into(), 8.875, true);
        let rates: Vec<TaxRate> = ctx.db.tax_rates().iter().collect();
        assert_eq!(rates.len(), 1);
        let r = &rates[0];
        assert!(r.id.starts_with("tax_"));
        assert_eq!(r.name, "Sales Tax");
        assert!((r.rate - 8.875).abs() < 0.001);
        assert!(r.is_default);
        assert_eq!(r.tenant_id, "t_tax");
        assert!(r.created_at > 0);
        assert_eq!(r.created_at, r.updated_at);
    }

    #[test]
    fn test_create_tax_rate_no_default() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t".into(), "Non-Default".into(), 5.0, false);
        let r = ctx.db.tax_rates().iter().next().unwrap();
        assert!(!r.is_default);
    }

    #[test]
    fn test_update_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t".into(), "Old".into(), 5.0, false);
        let id = ctx.db.tax_rates().iter().next().unwrap().id.clone();
        update_tax_rate(&ctx, id.clone(), "New".into(), 6.0, true);
        let updated = ctx.db.tax_rates().id().find(&id).unwrap();
        assert_eq!(updated.name, "New");
        assert!((updated.rate - 6.0).abs() < 0.001);
        assert!(updated.is_default);
    }

    #[test]
    fn test_update_nonexistent_tax_rate() {
        let ctx = test_ctx();
        update_tax_rate(&ctx, "tax_nonexistent".into(), "Nope".into(), 0.0, false);
        assert_eq!(ctx.db.tax_rates().iter().count(), 0);
    }

    #[test]
    fn test_tax_rate_default_clears_others() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t".into(), "Rate A".into(), 5.0, true);
        let a_id = ctx.db.tax_rates().iter().next().unwrap().id.clone();
        create_tax_rate(&ctx, "t".into(), "Rate B".into(), 8.0, true);
        let a = ctx.db.tax_rates().id().find(&a_id).unwrap();
        assert!(!a.is_default);
        let b = ctx.db.tax_rates().iter().find(|r| r.id != a_id).unwrap();
        assert!(b.is_default);
    }

    #[test]
    fn test_tax_rate_update_default_clears_others() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t".into(), "A".into(), 5.0, true);
        let a_id = ctx.db.tax_rates().iter().next().unwrap().id.clone();
        create_tax_rate(&ctx, "t".into(), "B".into(), 8.0, false);
        let b_id = ctx
            .db
            .tax_rates()
            .iter()
            .find(|r| r.id != a_id)
            .unwrap()
            .id
            .clone();
        update_tax_rate(&ctx, b_id, "B Updated".into(), 8.0, true);
        let a = ctx.db.tax_rates().id().find(&a_id).unwrap();
        assert!(!a.is_default);
    }

    #[test]
    fn test_delete_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t".into(), "Del".into(), 3.0, false);
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
}
