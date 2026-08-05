// TODO (kanban): Replace 18 unwrap() call(s) with proper error handling
use spacetimedb::*;

#[spacetimedb::table(accessor = user, public)]
#[derive(Debug, Clone)]
pub struct User {
    #[primary_key]
    pub id: String,
    #[unique]
    pub name: String,
    #[unique]
    pub email: String,
    pub role: String,
    pub pin: String,
    pub password_hash: String,
    pub active: bool,
    pub totp_secret: String,
    pub totp_enabled: bool,
    pub created_at: u64,
}

#[spacetimedb::table(accessor = user_settings, public)]
#[derive(Debug, Clone)]
pub struct UserSettings {
    #[primary_key]
    pub user_id: String,
    pub theme: String,
    pub default_ticket_status: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn create_user(ctx: &ReducerContext, name: String, email: String, role: String) {
    let id = super::make_id("user", ctx);
    ctx.db.user().insert(User {
        id,
        name,
        email,
        role,
        pin: String::new(),
        password_hash: String::new(),
        active: true,
        totp_secret: String::new(),
        totp_enabled: false,
        created_at: super::now_ms(ctx),
    });
}

#[spacetimedb::reducer]
pub fn update_user(
    ctx: &ReducerContext,
    id: String,
    name: String,
    email: String,
    role: String,
    active: bool,
) {
    if let Some(u) = ctx.db.user().id().find(&id) {
        ctx.db.user().id().update(User {
            name,
            email,
            role,
            active,
            ..u
        });
    }
}

#[spacetimedb::reducer]
pub fn set_user_password(ctx: &ReducerContext, id: String, password_hash: String) {
    if let Some(u) = ctx.db.user().id().find(&id) {
        ctx.db.user().id().update(User { password_hash, ..u });
    }
}

#[spacetimedb::reducer]
pub fn set_user_totp_secret(ctx: &ReducerContext, id: String, totp_secret: String) {
    if let Some(u) = ctx.db.user().id().find(&id) {
        ctx.db.user().id().update(User {
            totp_secret,
            totp_enabled: false,
            ..u
        });
    }
}

#[spacetimedb::reducer]
pub fn enable_user_totp(ctx: &ReducerContext, id: String) {
    if let Some(u) = ctx.db.user().id().find(&id) {
        ctx.db.user().id().update(User {
            totp_enabled: true,
            ..u
        });
    }
}

#[spacetimedb::reducer]
pub fn disable_user_totp(ctx: &ReducerContext, id: String) {
    if let Some(u) = ctx.db.user().id().find(&id) {
        ctx.db.user().id().update(User {
            totp_secret: String::new(),
            totp_enabled: false,
            ..u
        });
    }
}

#[spacetimedb::reducer]
pub fn set_user_pin(ctx: &ReducerContext, id: String, pin: String) {
    if let Some(u) = ctx.db.user().id().find(&id) {
        ctx.db.user().id().update(User { pin, ..u });
    }
}

#[spacetimedb::reducer]
pub fn delete_user(ctx: &ReducerContext, id: String) {
    ctx.db.user().id().delete(&id);
}

// ── UserSettings reducers ──

#[spacetimedb::reducer]
pub fn upsert_user_settings(
    ctx: &ReducerContext,
    user_id: String,
    theme: String,
    default_ticket_status: String,
) {
    let now = super::now_ms(ctx);
    if let Some(existing) = ctx.db.user_settings().user_id().find(&user_id) {
        ctx.db.user_settings().user_id().update(UserSettings {
            theme,
            default_ticket_status,
            updated_at: now,
            ..existing
        });
    } else {
        ctx.db.user_settings().insert(UserSettings {
            user_id,
            theme,
            default_ticket_status,
            created_at: now,
            updated_at: now,
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_user_settings(ctx: &ReducerContext, user_id: String) {
    ctx.db.user_settings().user_id().delete(&user_id);
}

#[cfg(test)]
mod tests {
    use super::*;

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
        assert!(u.password_hash.is_empty());
        assert!(!u.totp_enabled);
        assert!(u.pin.is_empty());
        assert!(u.created_at > 0);
    }

    #[test]
    fn test_update_user() {
        let ctx = test_ctx();
        create_user(&ctx, "bob".into(), "bob@t.com".into(), "tech".into());
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        update_user(
            &ctx,
            id.clone(),
            "bob_updated".into(),
            "bob@new.com".into(),
            "admin".into(),
            false,
        );
        let updated = ctx.db.user().id().find(&id).unwrap();
        assert_eq!(updated.name, "bob_updated");
        assert_eq!(updated.email, "bob@new.com");
        assert_eq!(updated.role, "admin");
        assert!(!updated.active);
    }

    #[test]
    fn test_update_nonexistent_user() {
        let ctx = test_ctx();
        update_user(
            &ctx,
            "user_nope".into(),
            "n".into(),
            "n@t.com".into(),
            "tech".into(),
            true,
        );
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_delete_user() {
        let ctx = test_ctx();
        create_user(&ctx, "eve".into(), "e@t.com".into(), "tech".into());
        assert_eq!(ctx.db.user().iter().count(), 1);
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        delete_user(&ctx, id);
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_user() {
        let ctx = test_ctx();
        delete_user(&ctx, "user_nope".into());
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_set_user_password() {
        let ctx = test_ctx();
        create_user(&ctx, "charlie".into(), "c@t.com".into(), "fd".into());
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
    fn test_set_user_password_nonexistent() {
        let ctx = test_ctx();
        set_user_password(&ctx, "user_nope".into(), "hash".into());
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_user_totp_lifecycle() {
        let ctx = test_ctx();
        create_user(&ctx, "dave".into(), "d@t.com".into(), "admin".into());
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        assert!(!ctx.db.user().id().find(&id).unwrap().totp_enabled);
        set_user_totp_secret(&ctx, id.clone(), "TEST_SECRET".into());
        let u = ctx.db.user().id().find(&id).unwrap();
        assert_eq!(u.totp_secret, "TEST_SECRET");
        assert!(!u.totp_enabled);
        enable_user_totp(&ctx, id.clone());
        assert!(ctx.db.user().id().find(&id).unwrap().totp_enabled);
        disable_user_totp(&ctx, id.clone());
        let u2 = ctx.db.user().id().find(&id).unwrap();
        assert!(!u2.totp_enabled);
        assert!(u2.totp_secret.is_empty());
    }

    #[test]
    fn test_set_user_pin() {
        let ctx = test_ctx();
        create_user(&ctx, "pin_user".into(), "pin@test.com".into(), "fd".into());
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        assert!(ctx.db.user().id().find(&id).unwrap().pin.is_empty());
        set_user_pin(&ctx, id.clone(), "4321".into());
        assert_eq!(ctx.db.user().id().find(&id).unwrap().pin, "4321");
    }

    #[test]
    fn test_upsert_user_settings_create() {
        let ctx = test_ctx();
        create_user(
            &ctx,
            "settings_test".into(),
            "s@test.com".into(),
            "tech".into(),
        );
        let uid = ctx.db.user().iter().next().unwrap().id.clone();
        upsert_user_settings(&ctx, uid.clone(), "dark".into(), "in_progress".into());
        let settings: Vec<UserSettings> = ctx.db.user_settings().iter().collect();
        assert_eq!(settings.len(), 1);
        let s = &settings[0];
        assert_eq!(s.user_id, uid);
        assert_eq!(s.theme, "dark");
        assert_eq!(s.default_ticket_status, "in_progress");
        assert!(s.created_at > 0);
        assert_eq!(s.created_at, s.updated_at);
    }

    #[test]
    fn test_upsert_user_settings_update() {
        let ctx = test_ctx();
        create_user(&ctx, "upd".into(), "upd@t.com".into(), "admin".into());
        let uid = ctx.db.user().iter().next().unwrap().id.clone();
        upsert_user_settings(&ctx, uid.clone(), "light".into(), "new".into());
        assert_eq!(ctx.db.user_settings().iter().count(), 1);
        upsert_user_settings(&ctx, uid.clone(), "dark".into(), "in_progress".into());
        assert_eq!(ctx.db.user_settings().iter().count(), 1);
        let updated = ctx.db.user_settings().user_id().find(&uid).unwrap();
        assert_eq!(updated.theme, "dark");
        assert!(updated.updated_at >= updated.created_at);
    }

    #[test]
    fn test_delete_user_settings() {
        let ctx = test_ctx();
        create_user(&ctx, "del_s".into(), "ds@t.com".into(), "tech".into());
        let uid = ctx.db.user().iter().next().unwrap().id.clone();
        upsert_user_settings(&ctx, uid.clone(), "dark".into(), "new".into());
        assert_eq!(ctx.db.user_settings().iter().count(), 1);
        delete_user_settings(&ctx, uid);
        assert_eq!(ctx.db.user_settings().iter().count(), 0);
    }
}
