use spacetimedb::*;

#[table(name = "audit_log", accessor = audit_log, public)]
#[derive(Debug, Clone)]
pub struct AuditLog {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub user_id: String,
    pub user_name: String,
    pub action: String,
    pub entity: String,
    pub entity_id: String,
    pub details: String,
    pub created_at: u64,
}

#[reducer]
pub fn log_audit(
    ctx: &ReducerContext,
    tenant_id: String,
    user_id: String,
    user_name: String,
    action: String,
    entity: String,
    entity_id: String,
    details: String,
) {
    let id = super::make_id("aud", ctx);
    let now = super::now_ms(ctx);
    ctx.db.audit_log().insert(AuditLog {
        id,
        tenant_id,
        user_id,
        user_name,
        action,
        entity,
        entity_id,
        details,
        created_at: now,
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_log_audit() {
        let ctx = test_ctx();
        log_audit(
            &ctx,
            "t_aud".into(),
            "user_1".into(),
            "Alice".into(),
            "created".into(),
            "customer".into(),
            "cust_1".into(),
            r#"{"name":"Alice"}"#.into(),
        );
        let logs: Vec<AuditLog> = ctx.db.audit_log().iter().collect();
        assert_eq!(logs.len(), 1);
        let l = &logs[0];
        assert!(l.id.starts_with("aud_"));
        assert_eq!(l.tenant_id, "t_aud");
        assert_eq!(l.user_id, "user_1");
        assert_eq!(l.user_name, "Alice");
        assert_eq!(l.action, "created");
        assert_eq!(l.entity, "customer");
        assert_eq!(l.entity_id, "cust_1");
        assert_eq!(l.details, r#"{"name":"Alice"}"#);
        assert!(l.created_at > 0);
    }

    #[test]
    fn test_log_multiple_audit_entries() {
        let ctx = test_ctx();
        log_audit(
            &ctx,
            "t".into(),
            "u1".into(),
            "A".into(),
            "create".into(),
            "ticket".into(),
            "tkt_1".into(),
            "".into(),
        );
        log_audit(
            &ctx,
            "t".into(),
            "u2".into(),
            "B".into(),
            "update".into(),
            "ticket".into(),
            "tkt_1".into(),
            r#"{"status":"completed"}"#.into(),
        );
        log_audit(
            &ctx,
            "t".into(),
            "u1".into(),
            "A".into(),
            "delete".into(),
            "ticket".into(),
            "tkt_1".into(),
            "".into(),
        );
        assert_eq!(ctx.db.audit_log().iter().count(), 3);
        let actions: Vec<String> = ctx
            .db
            .audit_log()
            .iter()
            .map(|l| l.action.clone())
            .collect();
        assert_eq!(actions, vec!["create", "update", "delete"]);
    }

    #[test]
    fn test_audit_log_tenant_isolation() {
        let ctx = test_ctx();
        log_audit(
            &ctx,
            "t_a".into(),
            "u1".into(),
            "A".into(),
            "login".into(),
            "user".into(),
            "u1".into(),
            "".into(),
        );
        log_audit(
            &ctx,
            "t_b".into(),
            "u2".into(),
            "B".into(),
            "login".into(),
            "user".into(),
            "u2".into(),
            "".into(),
        );
        let a_only: Vec<AuditLog> = ctx
            .db
            .audit_log()
            .iter()
            .filter(|l| l.tenant_id == "t_a")
            .collect();
        assert_eq!(a_only.len(), 1);
    }
}
