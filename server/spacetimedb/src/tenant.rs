use spacetimedb::*;

#[spacetimedb::table(accessor = tenants, public)]
#[derive(Debug, Clone)]
pub struct Tenant {
    #[primary_key]
    pub id: String,
    /// Display name (e.g. "Joe's Repair Shop")
    pub name: String,
    /// URL-safe slug (e.g. "joes-repair")
    #[unique]
    pub slug: String,
    /// Optional logo URL
    pub logo_url: String,
    /// JSON settings blob
    pub settings: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::table(accessor = tenant_members, public)]
#[derive(Debug, Clone)]
pub struct TenantMember {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    /// User.username that belongs to this tenant
    pub username: String,
    /// Role within the tenant: "admin" or "user"
    pub role: String,
    pub created_at: u64,
}

#[spacetimedb::reducer]
pub fn create_tenant(ctx: &ReducerContext, name: String, slug: String) {
    let id = super::make_id("tnt", ctx);
    let now = super::now_ms(ctx);
    ctx.db.tenants().insert(Tenant {
        id,
        name,
        slug: slug.to_lowercase().replace(' ', "-"),
        logo_url: String::new(),
        settings: "{}".to_string(),
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_tenant(
    ctx: &ReducerContext,
    id: String,
    name: String,
    slug: String,
    logo_url: String,
    settings: String,
) {
    if let Some(t) = ctx.db.tenants().id().find(&id) {
        ctx.db.tenants().id().update(Tenant {
            name,
            slug: slug.to_lowercase().replace(' ', "-"),
            logo_url,
            settings,
            updated_at: super::now_ms(ctx),
            ..t
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_tenant(ctx: &ReducerContext, id: String) {
    // Remove all members first
    let members: Vec<TenantMember> = ctx
        .db
        .tenant_members()
        .iter()
        .filter(|m| m.tenant_id == id)
        .collect();
    for m in members {
        ctx.db.tenant_members().id().delete(&m.id);
    }
    ctx.db.tenants().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn add_tenant_member(ctx: &ReducerContext, tenant_id: String, username: String, role: String) {
    let id = format!(
        "tmem_{}_{}",
        super::now_ms(ctx),
        ctx.sender().to_hex().chars().take(8).collect::<String>()
    );
    let now = super::now_ms(ctx);
    ctx.db.tenant_members().insert(TenantMember {
        id,
        tenant_id,
        username,
        role,
        created_at: now,
    });
}

#[spacetimedb::reducer]
pub fn remove_tenant_member(ctx: &ReducerContext, id: String) {
    ctx.db.tenant_members().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn update_tenant_member_role(ctx: &ReducerContext, id: String, role: String) {
    if let Some(m) = ctx.db.tenant_members().id().find(&id) {
        ctx.db
            .tenant_members()
            .id()
            .update(TenantMember { role, ..m });
    }
}

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_tenant() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Joe's Repair Shop".into(), "joes-repair".into());
        let tenants: Vec<Tenant> = ctx.db.tenants().iter().collect();
        assert_eq!(tenants.len(), 1);
        let t = &tenants[0];
        assert!(t.id.starts_with("tnt_"));
        assert_eq!(t.name, "Joe's Repair Shop");
        assert_eq!(t.slug, "joes-repair");
        assert_eq!(t.settings, "{}");
    }

    #[test]
    fn test_create_tenant_slug_normalization() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Test".into(), "My Shop 123".into());
        let t = ctx.db.tenants().iter().next().expect("expected tenant");
        assert_eq!(t.slug, "my-shop-123", "slug should be lowercased with spaces replaced by hyphens");
    }

    #[test]
    fn test_update_tenant() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Old Name".into(), "old".into());
        let t = ctx.db.tenants().iter().next().expect("expected tenant");
        let id = t.id.clone();
        update_tenant(&ctx, id.clone(), "New Name".into(), "new-slug".into(), "https://logo.url".into(), "{\"theme\":\"dark\"}".into());
        let updated = ctx.db.tenants().id().find(&id).expect("expected to exist");
        assert_eq!(updated.name, "New Name");
        assert_eq!(updated.slug, "new-slug");
        assert_eq!(updated.logo_url, "https://logo.url");
        assert_eq!(updated.settings, "{\"theme\":\"dark\"}");
    }

    #[test]
    fn test_delete_tenant_removes_members() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Test".into(), "test".into());
        let t = ctx.db.tenants().iter().next().expect("expected tenant");
        let tid = t.id.clone();
        add_tenant_member(&ctx, tid.clone(), "user1".into(), "admin".into());
        add_tenant_member(&ctx, tid.clone(), "user2".into(), "user".into());
        assert_eq!(ctx.db.tenant_members().iter().count(), 2);
        delete_tenant(&ctx, tid);
        assert_eq!(ctx.db.tenants().iter().count(), 0);
        assert_eq!(ctx.db.tenant_members().iter().count(), 0, "members should cascade");
    }

    #[test]
    fn test_add_tenant_member() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Test".into(), "test".into());
        let tid = ctx.db.tenants().iter().next().expect("expected tenant").id.clone();
        add_tenant_member(&ctx, tid.clone(), "alice".into(), "admin".into());
        let members: Vec<TenantMember> = ctx.db.tenant_members().iter().collect();
        assert_eq!(members.len(), 1);
        let m = &members[0];
        assert!(m.id.starts_with("tmem_"));
        assert_eq!(m.tenant_id, tid);
        assert_eq!(m.username, "alice");
        assert_eq!(m.role, "admin");
    }

    #[test]
    fn test_remove_tenant_member() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Test".into(), "test".into());
        let tid = ctx.db.tenants().iter().next().expect("expected tenant").id.clone();
        add_tenant_member(&ctx, tid.clone(), "bob".into(), "user".into());
        let mid = ctx.db.tenant_members().iter().next().expect("expected member").id.clone();
        remove_tenant_member(&ctx, mid);
        assert_eq!(ctx.db.tenant_members().iter().count(), 0);
    }

    #[test]
    fn test_update_tenant_member_role() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Test".into(), "test".into());
        let tid = ctx.db.tenants().iter().next().expect("expected tenant").id.clone();
        add_tenant_member(&ctx, tid, "charlie".into(), "user".into());
        let mid = ctx.db.tenant_members().iter().next().expect("expected member").id.clone();
        update_tenant_member_role(&ctx, mid.clone(), "admin".into());
        let updated = ctx.db.tenant_members().id().find(&mid).expect("expected to exist");
        assert_eq!(updated.role, "admin");
    }

    #[test]
    fn test_delete_nonexistent_tenant() {
        let ctx = test_ctx();
        delete_tenant(&ctx, "tnt_nonexistent".into());
        assert_eq!(ctx.db.tenants().iter().count(), 0);
    }
}
