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
