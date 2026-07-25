use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::*;

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
        assert_eq!(
            t.slug, "my-shop-123",
            "slug should be lowercased with spaces replaced by hyphens"
        );
    }

    #[test]
    fn test_update_tenant() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Old Name".into(), "old".into());
        let t = ctx.db.tenants().iter().next().expect("expected tenant");
        let id = t.id.clone();
        update_tenant(
            &ctx,
            id.clone(),
            "New Name".into(),
            "new-slug".into(),
            "https://logo.url".into(),
            "{\"theme\":\"dark\"}".into(),
        );
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
        assert_eq!(
            ctx.db.tenant_members().iter().count(),
            0,
            "members should cascade"
        );
    }

    #[test]
    fn test_add_tenant_member() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Test".into(), "test".into());
        let tid = ctx
            .db
            .tenants()
            .iter()
            .next()
            .expect("expected tenant")
            .id
            .clone();
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
        let tid = ctx
            .db
            .tenants()
            .iter()
            .next()
            .expect("expected tenant")
            .id
            .clone();
        add_tenant_member(&ctx, tid.clone(), "bob".into(), "user".into());
        let mid = ctx
            .db
            .tenant_members()
            .iter()
            .next()
            .expect("expected member")
            .id
            .clone();
        remove_tenant_member(&ctx, mid);
        assert_eq!(ctx.db.tenant_members().iter().count(), 0);
    }

    #[test]
    fn test_update_tenant_member_role() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Test".into(), "test".into());
        let tid = ctx
            .db
            .tenants()
            .iter()
            .next()
            .expect("expected tenant")
            .id
            .clone();
        add_tenant_member(&ctx, tid, "charlie".into(), "user".into());
        let mid = ctx
            .db
            .tenant_members()
            .iter()
            .next()
            .expect("expected member")
            .id
            .clone();
        update_tenant_member_role(&ctx, mid.clone(), "admin".into());
        let updated = ctx
            .db
            .tenant_members()
            .id()
            .find(&mid)
            .expect("expected to exist");
        assert_eq!(updated.role, "admin");
    }

    #[test]
    fn test_delete_nonexistent_tenant() {
        let ctx = test_ctx();
        delete_tenant(&ctx, "tnt_nonexistent".into());
        assert_eq!(ctx.db.tenants().iter().count(), 0);
    }
}
