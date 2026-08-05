// TODO (kanban): Replace 9 unwrap() call(s) with proper error handling
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

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_tenant() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Joe's Repair".into(), "joes-repair".into());
        let tenants: Vec<Tenant> = ctx.db.tenants().iter().collect();
        assert_eq!(tenants.len(), 1);
        let t = &tenants[0];
        assert!(t.id.starts_with("tnt_"));
        assert_eq!(t.name, "Joe's Repair");
        assert_eq!(t.slug, "joes-repair");
        assert!(t.logo_url.is_empty());
        assert_eq!(t.settings, "{}");
        assert!(t.created_at > 0);
        assert_eq!(t.created_at, t.updated_at);
    }

    #[test]
    fn test_create_tenant_slug_normalization() {
        let ctx = test_ctx();
        create_tenant(&ctx, "My Shop".into(), "My Shop With Spaces".into());
        let t = ctx.db.tenants().iter().next().unwrap();
        assert_eq!(t.slug, "my-shop-with-spaces");
    }

    #[test]
    fn test_update_tenant() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Old Shop".into(), "old-shop".into());
        let id = ctx.db.tenants().iter().next().unwrap().id.clone();
        update_tenant(
            &ctx,
            id.clone(),
            "New Shop".into(),
            "new-shop".into(),
            "https://logo.url".into(),
            r#"{"theme":"dark"}"#.into(),
        );
        let updated = ctx.db.tenants().id().find(&id).unwrap();
        assert_eq!(updated.name, "New Shop");
        assert_eq!(updated.slug, "new-shop");
        assert_eq!(updated.logo_url, "https://logo.url");
        assert_eq!(updated.settings, r#"{"theme":"dark"}"#);
    }

    #[test]
    fn test_update_nonexistent_tenant() {
        let ctx = test_ctx();
        update_tenant(
            &ctx,
            "tnt_nope".into(),
            "N".into(),
            "n".into(),
            "".into(),
            "{}".into(),
        );
        assert_eq!(ctx.db.tenants().iter().count(), 0);
    }

    #[test]
    fn test_delete_tenant() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Del Shop".into(), "del-shop".into());
        let id = ctx.db.tenants().iter().next().unwrap().id.clone();
        add_tenant_member(&ctx, id.clone(), "user_1".into(), "admin".into());
        assert_eq!(ctx.db.tenants().iter().count(), 1);
        assert_eq!(ctx.db.tenant_members().iter().count(), 1);
        delete_tenant(&ctx, id);
        assert_eq!(ctx.db.tenants().iter().count(), 0);
        assert_eq!(ctx.db.tenant_members().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_tenant() {
        let ctx = test_ctx();
        delete_tenant(&ctx, "tnt_nope".into());
        assert_eq!(ctx.db.tenants().iter().count(), 0);
    }

    #[test]
    fn test_add_remove_tenant_member() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Shop".into(), "shop".into());
        let tid = ctx.db.tenants().iter().next().unwrap().id.clone();
        add_tenant_member(&ctx, tid, "tech_1".into(), "user".into());
        assert_eq!(ctx.db.tenant_members().iter().count(), 1);
        let m = ctx.db.tenant_members().iter().next().unwrap();
        assert_eq!(m.username, "tech_1");
        assert_eq!(m.role, "user");
        remove_tenant_member(&ctx, m.id.clone());
        assert_eq!(ctx.db.tenant_members().iter().count(), 0);
    }

    #[test]
    fn test_remove_nonexistent_member() {
        let ctx = test_ctx();
        remove_tenant_member(&ctx, "tmem_nope".into());
        assert_eq!(ctx.db.tenant_members().iter().count(), 0);
    }

    #[test]
    fn test_update_tenant_member_role() {
        let ctx = test_ctx();
        create_tenant(&ctx, "S".into(), "s".into());
        add_tenant_member(
            &ctx,
            ctx.db.tenants().iter().next().unwrap().id.clone(),
            "admin_u".into(),
            "user".into(),
        );
        let member = ctx.db.tenant_members().iter().next().unwrap();
        assert_eq!(member.role, "user");
        update_tenant_member_role(&ctx, member.id.clone(), "admin".into());
        assert_eq!(
            ctx.db.tenant_members().id().find(&member.id).unwrap().role,
            "admin"
        );
    }

    #[test]
    fn test_update_nonexistent_member_role() {
        let ctx = test_ctx();
        update_tenant_member_role(&ctx, "tmem_nope".into(), "admin".into());
        assert_eq!(ctx.db.tenant_members().iter().count(), 0);
    }

    #[test]
    fn test_multiple_tenants() {
        let ctx = test_ctx();
        create_tenant(&ctx, "A".into(), "a".into());
        create_tenant(&ctx, "B".into(), "b".into());
        create_tenant(&ctx, "C".into(), "c".into());
        assert_eq!(ctx.db.tenants().iter().count(), 3);
    }
}
