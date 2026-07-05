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
pub fn update_user(ctx: &ReducerContext, id: String, name: String, email: String, role: String, active: bool) {
    if let Some(u) = ctx.db.user().id().find(&id) {
        ctx.db.user().id().update(User { name, email, role, active, ..u });
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
        ctx.db.user().id().update(User { totp_secret, totp_enabled: false, ..u });
    }
}

#[spacetimedb::reducer]
pub fn enable_user_totp(ctx: &ReducerContext, id: String) {
    if let Some(u) = ctx.db.user().id().find(&id) {
        ctx.db.user().id().update(User { totp_enabled: true, ..u });
    }
}

#[spacetimedb::reducer]
pub fn disable_user_totp(ctx: &ReducerContext, id: String) {
    if let Some(u) = ctx.db.user().id().find(&id) {
        ctx.db.user().id().update(User { totp_secret: String::new(), totp_enabled: false, ..u });
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
pub fn upsert_user_settings(ctx: &ReducerContext, user_id: String, theme: String, default_ticket_status: String) {
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
