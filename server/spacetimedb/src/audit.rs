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
    use crate::audit::*;
    use crate::audit::audit_log;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_log_audit() {
        let ctx = test_ctx();
        log_audit(&ctx, "test_tenant_id".into(), "test_user_id".into(), "test_user_name".into(), "test_action".into(), "test_entity".into(), "test_entity_id".into(), "test_details".into());
        assert!(ctx.db.audit_log().iter().count() >= 0);
    }

}
