use spacetimedb::*;

#[spacetimedb::table(accessor = sla_configs, public)]
#[derive(Debug, Clone)]
pub struct SlaConfig {
    #[primary_key]
    pub tenant_id: String,
    /// JSON object: {"urgent": 4, "high": 24, "medium": 72, "low": 120}
    pub targets_json: String,
    pub updated_at: u64,
    pub updated_by: String,
}

#[spacetimedb::reducer]
pub fn upsert_sla_config(ctx: &ReducerContext, tenant_id: String, targets_json: String) {
    let now = super::now_ms(ctx);
    let caller = ctx.sender().to_string();
    if let Some(existing) = ctx.db.sla_configs().tenant_id().find(&tenant_id) {
        ctx.db.sla_configs().tenant_id().update(SlaConfig {
            targets_json,
            updated_at: now,
            updated_by: caller,
            ..existing
        });
    } else {
        ctx.db.sla_configs().insert(SlaConfig {
            tenant_id,
            targets_json,
            updated_at: now,
            updated_by: caller,
        });
    }
}

#[cfg(test)]
mod sla_config_tests {
    use super::*;

    #[test]
    fn test_sla_config_basic() {
        // TODO: implement basic test
        assert!(true);
    }
}
