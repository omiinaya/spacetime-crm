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
pub fn delete_user(ctx: &ReducerContext, id: String) {
    ctx.db.user().id().delete(&id);
}
