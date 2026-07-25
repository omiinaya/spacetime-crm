use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::user::user;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_user() {
        let ctx = test_ctx();
        create_user(&ctx, "alice".into(), "alice@test.com".into(), "tech".into());
        let users: Vec<User> = ctx.db.user().iter().collect();
        assert_eq!(users.len(), 1);
        let u = &users[0];
        assert!(u.id.starts_with("user_"));
        assert_eq!(u.name, "alice");
        assert_eq!(u.email, "alice@test.com");
        assert_eq!(u.role, "tech");
        assert!(u.active);
        assert!(!u.totp_enabled);
        assert!(u.created_at > 0);
    }

    #[test]
    fn test_create_user_defaults() {
        let ctx = test_ctx();
        create_user(&ctx, "bob".into(), "bob@test.com".into(), "admin".into());
        let u = ctx.db.user().iter().next().unwrap();
        assert!(u.pin.is_empty());
        assert!(u.password_hash.is_empty());
        assert!(u.totp_secret.is_empty());
        assert!(!u.totp_enabled);
        assert!(u.active);
    }

    #[test]
    fn test_update_user() {
        let ctx = test_ctx();
        create_user(&ctx, "carol".into(), "carol@test.com".into(), "tech".into());
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        update_user(
            &ctx,
            id.clone(),
            "charlie".into(),
            "charlie@test.com".into(),
            "admin".into(),
            false,
        );
        let updated = ctx.db.user().id().find(&id).unwrap();
        assert_eq!(updated.name, "charlie");
        assert_eq!(updated.email, "charlie@test.com");
        assert_eq!(updated.role, "admin");
        assert!(!updated.active);
    }

    #[test]
    fn test_update_nonexistent_user() {
        let ctx = test_ctx();
        update_user(
            &ctx,
            "user_nonexistent".into(),
            "Nope".into(),
            "nope@test.com".into(),
            "admin".into(),
            true,
        );
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_set_user_password() {
        let ctx = test_ctx();
        create_user(&ctx, "dave".into(), "dave@test.com".into(), "tech".into());
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        assert!(ctx
            .db
            .user()
            .id()
            .find(&id)
            .unwrap()
            .password_hash
            .is_empty());
        set_user_password(&ctx, id.clone(), "bcrypt_hash".into());
        assert_eq!(
            ctx.db.user().id().find(&id).unwrap().password_hash,
            "bcrypt_hash"
        );
    }

    #[test]
    fn test_set_password_nonexistent_user() {
        let ctx = test_ctx();
        set_user_password(&ctx, "user_nonexistent".into(), "hash".into());
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_user_totp_lifecycle() {
        let ctx = test_ctx();
        create_user(&ctx, "eve".into(), "eve@test.com".into(), "admin".into());
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        set_user_totp_secret(&ctx, id.clone(), "JBSWY3DPEHPK3PXP".into());
        let u = ctx.db.user().id().find(&id).unwrap();
        assert_eq!(u.totp_secret, "JBSWY3DPEHPK3PXP");
        assert!(!u.totp_enabled);
        enable_user_totp(&ctx, id.clone());
        assert!(ctx.db.user().id().find(&id).unwrap().totp_enabled);
        disable_user_totp(&ctx, id.clone());
        let u = ctx.db.user().id().find(&id).unwrap();
        assert!(!u.totp_enabled);
        assert!(u.totp_secret.is_empty());
    }

    #[test]
    fn test_set_user_pin() {
        let ctx = test_ctx();
        create_user(&ctx, "frank".into(), "frank@test.com".into(), "tech".into());
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        set_user_pin(&ctx, id.clone(), "4321".into());
        assert_eq!(ctx.db.user().id().find(&id).unwrap().pin, "4321");
    }

    #[test]
    fn test_set_pin_nonexistent_user() {
        let ctx = test_ctx();
        set_user_pin(&ctx, "user_nonexistent".into(), "1234".into());
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_delete_user() {
        let ctx = test_ctx();
        create_user(
            &ctx,
            "grace".into(),
            "grace@test.com".into(),
            "front_desk".into(),
        );
        assert_eq!(ctx.db.user().iter().count(), 1);
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        delete_user(&ctx, id);
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_user() {
        let ctx = test_ctx();
        delete_user(&ctx, "user_nonexistent".into());
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_upsert_user_settings() {
        let ctx = test_ctx();
        upsert_user_settings(&ctx, "u1".into(), "dark".into(), "in_progress".into());
        let settings: Vec<UserSettings> = ctx.db.user_settings().iter().collect();
        assert_eq!(settings.len(), 1);
        let s = &settings[0];
        assert_eq!(s.theme, "dark");
        assert_eq!(s.default_ticket_status, "in_progress");
        // Update
        upsert_user_settings(&ctx, "u1".into(), "light".into(), "new".into());
        assert_eq!(
            ctx.db.user_settings().iter().count(),
            1,
            "upsert should not create duplicate"
        );
        let updated = ctx
            .db
            .user_settings()
            .user_id()
            .find(&"u1".to_string())
            .unwrap();
        assert_eq!(updated.theme, "light");
    }

    #[test]
    fn test_delete_user_settings() {
        let ctx = test_ctx();
        upsert_user_settings(&ctx, "u1".into(), "dark".into(), "new".into());
        assert_eq!(ctx.db.user_settings().iter().count(), 1);
        delete_user_settings(&ctx, "u1".into());
        assert_eq!(ctx.db.user_settings().iter().count(), 0);
    }
}
