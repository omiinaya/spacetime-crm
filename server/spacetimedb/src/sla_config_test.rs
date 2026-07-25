use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::sla_config::sla_configs;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_upsert_sla_config_insert() {
        let ctx = test_ctx();
        upsert_sla_config(
            &ctx,
            "t_sla".into(),
            r#"{"urgent":4,"high":24,"medium":72,"low":120}"#.into(),
        );
        let configs: Vec<SlaConfig> = ctx.db.sla_configs().iter().collect();
        assert_eq!(configs.len(), 1);
        let c = &configs[0];
        assert_eq!(c.tenant_id, "t_sla");
        assert_eq!(
            c.targets_json,
            r#"{"urgent":4,"high":24,"medium":72,"low":120}"#
        );
        assert!(c.updated_at > 0);
    }

    #[test]
    fn test_upsert_sla_config_update() {
        let ctx = test_ctx();
        upsert_sla_config(&ctx, "t_1".into(), r#"{"urgent":4}"#.into());
        let orig_updated = ctx.db.sla_configs().iter().next().unwrap().updated_at;
        upsert_sla_config(&ctx, "t_1".into(), r#"{"urgent":2}"#.into());
        let configs: Vec<SlaConfig> = ctx.db.sla_configs().iter().collect();
        assert_eq!(configs.len(), 1, "upsert should not create duplicate");
        assert_eq!(configs[0].targets_json, r#"{"urgent":2}"#);
        assert!(configs[0].updated_at >= orig_updated);
    }

    #[test]
    fn test_upsert_sla_config_multi_tenant() {
        let ctx = test_ctx();
        upsert_sla_config(&ctx, "t_a".into(), r#"{"urgent":4}"#.into());
        upsert_sla_config(&ctx, "t_b".into(), r#"{"urgent":8}"#.into());
        assert_eq!(ctx.db.sla_configs().iter().count(), 2);
        let t_b = ctx
            .db
            .sla_configs()
            .tenant_id()
            .find(&"t_b".to_string())
            .expect("expected t_b");
        assert_eq!(t_b.targets_json, r#"{"urgent":8}"#);
    }

    #[test]
    fn test_upsert_sla_config_empty_targets() {
        let ctx = test_ctx();
        upsert_sla_config(&ctx, "t_1".into(), "{}".into());
        let c = ctx.db.sla_configs().iter().next().expect("expected config");
        assert_eq!(c.targets_json, "{}");
    }
}
