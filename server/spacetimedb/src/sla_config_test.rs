#[cfg(test)]
mod tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_upsert_sla_config_insert() {
        let ctx = test_ctx();
        upsert_sla_config(&ctx, "t_1".into(), r#"{"urgent":4,"high":24}"#.into());
        let configs: Vec<SlaConfig> = ctx.db.sla_configs().iter().collect();
        assert_eq!(configs.len(), 1);
        let c = &configs[0];
        assert_eq!(c.tenant_id, "t_1");
        assert_eq!(c.targets_json, r#"{"urgent":4,"high":24}"#);
        assert!(c.updated_at > 0);
        assert!(!c.updated_by.is_empty());
    }

    #[test]
    fn test_upsert_sla_config_update() {
        let ctx = test_ctx();
        upsert_sla_config(&ctx, "t_1".into(), r#"{"urgent":4}"#.into());
        let orig = ctx
            .db
            .sla_configs()
            .iter()
            .next()
            .expect("expected record")
            .updated_at;
        upsert_sla_config(&ctx, "t_1".into(), r#"{"urgent":2}"#.into());
        let configs: Vec<SlaConfig> = ctx.db.sla_configs().iter().collect();
        assert_eq!(configs.len(), 1, "should be upsert, not duplicate");
        let c = &configs[0];
        assert_eq!(c.targets_json, r#"{"urgent":2}"#);
        assert!(c.updated_at >= orig, "updated_at should be newer");
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
}
