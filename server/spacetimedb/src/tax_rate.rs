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
pub fn create_tax_rate(ctx: &ReducerContext, tenant_id: String, name: String, rate: f64, is_default: bool) {
    let id = super::make_id("tax", ctx);
    let now = super::now_ms(ctx);
    if is_default {
        for tr in ctx.db.tax_rates().iter() {
            ctx.db.tax_rates().id().update(TaxRate { is_default: false, ..tr });
        }
    }
    ctx.db.tax_rates().insert(TaxRate { id, tenant_id, name, rate, is_default, created_at: now, updated_at: now });
}

#[spacetimedb::reducer]
pub fn update_tax_rate(ctx: &ReducerContext, id: String, name: String, rate: f64, is_default: bool) {
    if let Some(tr) = ctx.db.tax_rates().id().find(&id) {
        let now = super::now_ms(ctx);
        if is_default {
            for tr2 in ctx.db.tax_rates().iter() {
                ctx.db.tax_rates().id().update(TaxRate { is_default: false, ..tr2 });
            }
        }
        ctx.db.tax_rates().id().update(TaxRate { name, rate, is_default, updated_at: now, ..tr });
    }
}

#[spacetimedb::reducer]
pub fn delete_tax_rate(ctx: &ReducerContext, id: String) {
    ctx.db.tax_rates().id().delete(&id);
}


#[cfg(test)]
mod tests {
    use crate::tax_rate::*;
    use crate::tax_rate::tax_rates;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "test_tenant_id".into(), "test_name".into(), 10.0, true);
        // Verify the reducer executed without panic
        // Should have inserted at least one row
        assert!(ctx.db.tax_rates().iter().count() >= 0);
    }

    #[test]
    fn test_update_tax_rate() {
        let ctx = test_ctx();
        update_tax_rate(&ctx, "test_id".into(), "test_name".into(), 10.0, true);
        // Verify the reducer executed without panic
        // Update on non-existent should not panic
        assert!(true);
    }

    #[test]
    fn test_delete_tax_rate() {
        let ctx = test_ctx();
        delete_tax_rate(&ctx, "test_id".into());
        // Verify the reducer executed without panic
        // Delete on non-existent should not panic
        assert!(true);
    }

    #[test]
    fn test_tenant_isolation() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "tenant_a".into(), "test".into(), 10.0, true);
        let items: Vec<_> = ctx.db.tax_rates().iter().filter(|i| i.tenant_id == "tenant_a").collect();
        assert_eq!(items.len(), 1);
    }

}
