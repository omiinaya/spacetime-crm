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
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_save_push_subscription() {
        let ctx = test_ctx();
        save_push_subscription(
            &ctx,
            "u_1".into(),
            "t_1".into(),
            "https://push.example.com/endpoint".into(),
            "p256dh_value".into(),
            "auth_value".into(),
            "Mozilla/5.0".into(),
        );
        let subs: Vec<PushSubscription> = ctx.db.push_subscriptions().iter().collect();
        assert_eq!(subs.len(), 1);
        let s = &subs[0];
        assert!(s.id.starts_with("push_"), "id should start with push_");
        assert_eq!(s.user_id, "u_1");
        assert_eq!(s.tenant_id, "t_1");
        assert_eq!(s.endpoint, "https://push.example.com/endpoint");
        assert_eq!(s.p256dh_key, "p256dh_value");
        assert_eq!(s.auth_key, "auth_value");
        assert_eq!(s.user_agent, "Mozilla/5.0");
        assert!(s.created_at > 0, "created_at should be positive");
    }

    #[test]
    fn test_remove_push_subscription() {
        let ctx = test_ctx();
        save_push_subscription(
            &ctx,
            "u_1".into(),
            "t_1".into(),
            "ep1".into(),
            "k1".into(),
            "a1".into(),
            "ua".into(),
        );
        let id = ctx
            .db
            .push_subscriptions()
            .iter()
            .next()
            .expect("expected a subscription")
            .id
            .clone();
        assert_eq!(ctx.db.push_subscriptions().iter().count(), 1);
        remove_push_subscription(&ctx, id);
        assert_eq!(ctx.db.push_subscriptions().iter().count(), 0);
    }

    #[test]
    fn test_remove_nonexistent_push_subscription_is_noop() {
        let ctx = test_ctx();
        remove_push_subscription(&ctx, "push_nonexistent".into());
        assert_eq!(ctx.db.push_subscriptions().iter().count(), 0);
    }

    #[test]
    fn test_remove_user_push_subscriptions_removes_all_for_user() {
        let ctx = test_ctx();
        for n in 0..3 {
            save_push_subscription(
                &ctx,
                "u_1".into(),
                "t_1".into(),
                format!("ep{n}"),
                format!("k{n}"),
                format!("a{n}"),
                "ua".into(),
            );
        }
        // Another user's subscription must survive.
        save_push_subscription(
            &ctx,
            "u_2".into(),
            "t_1".into(),
            "other_ep".into(),
            "other_k".into(),
            "other_a".into(),
            "ua".into(),
        );
        assert_eq!(ctx.db.push_subscriptions().iter().count(), 4);
        remove_user_push_subscriptions(&ctx, "u_1".into());
        let remaining: Vec<PushSubscription> = ctx.db.push_subscriptions().iter().collect();
        assert_eq!(remaining.len(), 1);
        assert_eq!(remaining[0].user_id, "u_2");
    }

    #[test]
    fn test_remove_user_push_subscriptions_noop_for_unknown_user() {
        let ctx = test_ctx();
        remove_user_push_subscriptions(&ctx, "u_ghost".into());
        assert_eq!(ctx.db.push_subscriptions().iter().count(), 0);
    }
}
