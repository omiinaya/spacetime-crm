use spacetimedb::*;

#[spacetimedb::table(accessor = tax_rates, public)]
#[derive(Debug, Clone)]
pub struct TaxRate {
    #[primary_key]
    pub id: String,
    pub name: String,
    pub rate: f64,
    pub is_default: bool,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn create_tax_rate(ctx: &ReducerContext, name: String, rate: f64, is_default: bool) {
    let id = super::make_id("tax", ctx);
    let now = super::now_ms(ctx);
    if is_default {
        for tr in ctx.db.tax_rates().iter() {
            ctx.db.tax_rates().id().update(TaxRate { is_default: false, ..tr });
        }
    }
    ctx.db.tax_rates().insert(TaxRate { id, name, rate, is_default, created_at: now, updated_at: now });
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
