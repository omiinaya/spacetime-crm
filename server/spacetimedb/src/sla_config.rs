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
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_upsert_sla_config_create() {
        let ctx = test_ctx();
        let targets = r#"{"urgent":4,"high":24,"medium":72,"low":120}"#;
        upsert_sla_config(&ctx, "t_sla".into(), targets.into());
        let configs: Vec<SlaConfig> = ctx.db.sla_configs().iter().collect();
        assert_eq!(configs.len(), 1);
        let c = &configs[0];
        assert_eq!(c.tenant_id, "t_sla");
        assert_eq!(c.targets_json, targets);
        assert!(c.updated_at > 0);
        assert!(!c.updated_by.is_empty());
    }

    #[test]
    fn test_upsert_sla_config_update() {
        let ctx = test_ctx();
        upsert_sla_config(&ctx, "t_sla".into(), r#"{"urgent":4}"#.into());
        assert_eq!(ctx.db.sla_configs().iter().count(), 1);
        upsert_sla_config(&ctx, "t_sla".into(), r#"{"urgent":2}"#.into());
        assert_eq!(ctx.db.sla_configs().iter().count(), 1);
        let updated = ctx
            .db
            .sla_configs()
            .tenant_id()
            .find(&"t_sla".into())
            .unwrap();
        assert_eq!(updated.targets_json, r#"{"urgent":2}"#);
    }

    #[test]
    fn test_upsert_sla_config_empty_targets() {
        let ctx = test_ctx();
        upsert_sla_config(&ctx, "t_sla".into(), "{}".into());
        let c = ctx.db.sla_configs().iter().next().unwrap();
        assert_eq!(c.targets_json, "{}");
    }

    #[test]
    fn test_sla_config_tenant_isolation() {
        let ctx = test_ctx();
        upsert_sla_config(&ctx, "t_a".into(), r#"{"urgent":1}"#.into());
        upsert_sla_config(&ctx, "t_b".into(), r#"{"urgent":4}"#.into());
        assert_eq!(ctx.db.sla_configs().iter().count(), 2);
        let a = ctx
            .db
            .sla_configs()
            .tenant_id()
            .find(&"t_a".into())
            .unwrap();
        assert_eq!(a.targets_json, r#"{"urgent":1}"#);
    }
}
