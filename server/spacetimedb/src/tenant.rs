use spacetimedb::*;

#[spacetimedb::table(accessor = tenants, public)]
#[derive(Debug, Clone)]
pub struct Tenant {
    #[primary_key]
    pub id: String,
    /// Display name (e.g. "Joe's Repair Shop")
    pub name: String,
    /// URL-safe slug (e.g. "joes-repair")
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
    let members: Vec<TenantMember> = ctx.db.tenant_members().iter()
        .filter(|m| m.tenant_id == id)
        .collect();
    for m in members {
        ctx.db.tenant_members().id().delete(&m.id);
    }
    ctx.db.tenants().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn add_tenant_member(ctx: &ReducerContext, tenant_id: String, username: String, role: String) {
    let id = format!("tmem_{}_{}", super::now_ms(ctx), ctx.sender().to_hex().chars().take(8).collect::<String>());
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
        ctx.db.tenant_members().id().update(TenantMember { role, ..m });
    }
}
