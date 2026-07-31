use spacetimedb::*;

#[spacetimedb::table(accessor = push_subscriptions, public)]
#[derive(Debug, Clone)]
pub struct PushSubscription {
    #[primary_key]
    pub id: String,
    pub user_id: String,
    pub tenant_id: String,
    pub endpoint: String,
    pub p256dh_key: String,
    pub auth_key: String,
    pub user_agent: String,
    pub created_at: u64,
}

#[spacetimedb::reducer]
pub fn save_push_subscription(
    ctx: &ReducerContext,
    user_id: String,
    tenant_id: String,
    endpoint: String,
    p256dh_key: String,
    auth_key: String,
    user_agent: String,
) {
    let id = super::make_id("push", ctx);
    ctx.db.push_subscriptions().insert(PushSubscription {
        id,
        user_id,
        tenant_id,
        endpoint,
        p256dh_key,
        auth_key,
        user_agent,
        created_at: super::now_ms(ctx),
    });
}

#[spacetimedb::reducer]
pub fn remove_push_subscription(ctx: &ReducerContext, id: String) {
    ctx.db.push_subscriptions().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn remove_user_push_subscriptions(ctx: &ReducerContext, user_id: String) {
    while let Some(sub) = ctx
        .db
        .push_subscriptions()
        .iter()
        .find(|s| s.user_id == user_id)
    {
        ctx.db.push_subscriptions().id().delete(&sub.id);
    }
}

#[cfg(test)]
mod push_subscription_tests {
    use super::*;

    #[test]
    fn test_push_subscription_basic() {
        // TODO: implement basic test
        assert!(true);
    }
}

#[cfg(test)]
mod push_subscription_tests {
    use super::*;

    #[test]
    fn test_push_subscription_basic() {
        // TODO: implement basic test
        assert!(true);
    }
}
