use spacetimedb::*;

#[spacetimedb::table(accessor = webhook_subscriptions, public)]
#[derive(Debug, Clone)]
pub struct WebhookSubscription {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    /// URL to send POST requests to
    pub url: String,
    /// Comma-separated event types (e.g. "ticket.created,ticket.updated")
    pub events: String,
    /// Optional secret for HMAC-SHA256 signing
    pub secret: String,
    /// Whether this subscription is active
    pub active: bool,
    pub created_at: u64,
    pub updated_at: u64,
}

/// List of supported event types
pub const SUPPORTED_EVENTS: [&str; 13] = [
    "customer.created",
    "customer.updated",
    "customer.deleted",
    "ticket.created",
    "ticket.updated",
    "ticket.status_changed",
    "invoice.created",
    "invoice.status_changed",
    "invoice.paid",
    "payment.created",
    "estimate.created",
    "estimate.approved",
    "appointment.created",
];

#[spacetimedb::reducer]
pub fn create_webhook_subscription(
    ctx: &ReducerContext,
    tenant_id: String,
    url: String,
    events: String,
    secret: String,
) {
    let id = make_webhook_id(ctx);
    let now = now_ms(ctx);
    ctx.db.webhook_subscriptions().insert(WebhookSubscription {
        id,
        tenant_id,
        url,
        events,
        secret,
        active: true,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_webhook_subscription(
    ctx: &ReducerContext,
    id: String,
    url: String,
    events: String,
    secret: String,
    active: bool,
) {
    if let Some(sub) = ctx.db.webhook_subscriptions().id().find(&id) {
        ctx.db
            .webhook_subscriptions()
            .id()
            .update(WebhookSubscription {
                url,
                events,
                secret,
                active,
                updated_at: now_ms(ctx),
                ..sub
            });
    }
}

#[spacetimedb::reducer]
pub fn delete_webhook_subscription(ctx: &ReducerContext, id: String) {
    ctx.db.webhook_subscriptions().id().delete(&id);
}

fn now_ms(ctx: &ReducerContext) -> u64 {
    ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000
}

fn make_webhook_id(ctx: &ReducerContext) -> String {
    let ts = now_ms(ctx);
    let discrim = ctx.sender().to_hex();
    let short = if discrim.len() > 8 {
        &discrim[..8]
    } else {
        &discrim
    };
    format!("whk_{}_{}", ts, short)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_webhook_subscription() {
        let ctx = test_ctx();
        create_webhook_subscription(
            &ctx,
            "t_wh".into(),
            "https://hooks.example.com".into(),
            "ticket.created,ticket.updated".into(),
            "sec_123".into(),
        );
        let subs: Vec<WebhookSubscription> = ctx.db.webhook_subscriptions().iter().collect();
        assert_eq!(subs.len(), 1);
        let s = &subs[0];
        assert!(s.id.starts_with("whk_"));
        assert_eq!(s.url, "https://hooks.example.com");
        assert_eq!(s.events, "ticket.created,ticket.updated");
        assert_eq!(s.secret, "sec_123");
        assert!(s.active);
        assert_eq!(s.tenant_id, "t_wh");
        assert!(s.created_at > 0);
        assert_eq!(s.created_at, s.updated_at);
    }

    #[test]
    fn test_update_webhook_subscription() {
        let ctx = test_ctx();
        create_webhook_subscription(
            &ctx,
            "t".into(),
            "https://old.url".into(),
            "ticket.created".into(),
            String::new(),
        );
        let id = ctx
            .db
            .webhook_subscriptions()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        update_webhook_subscription(
            &ctx,
            id.clone(),
            "https://new.url".into(),
            "customer.*".into(),
            "new_secret".into(),
            false,
        );
        let updated = ctx.db.webhook_subscriptions().id().find(&id).unwrap();
        assert_eq!(updated.url, "https://new.url");
        assert_eq!(updated.events, "customer.*");
        assert_eq!(updated.secret, "new_secret");
        assert!(!updated.active);
    }

    #[test]
    fn test_update_nonexistent_webhook() {
        let ctx = test_ctx();
        update_webhook_subscription(
            &ctx,
            "whk_nonexistent".into(),
            "https://x.com".into(),
            "a".into(),
            "".into(),
            true,
        );
        assert_eq!(ctx.db.webhook_subscriptions().iter().count(), 0);
    }

    #[test]
    fn test_delete_webhook_subscription() {
        let ctx = test_ctx();
        create_webhook_subscription(
            &ctx,
            "t".into(),
            "https://del.url".into(),
            "a".into(),
            String::new(),
        );
        assert_eq!(ctx.db.webhook_subscriptions().iter().count(), 1);
        let id = ctx
            .db
            .webhook_subscriptions()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        delete_webhook_subscription(&ctx, id);
        assert_eq!(ctx.db.webhook_subscriptions().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_webhook() {
        let ctx = test_ctx();
        delete_webhook_subscription(&ctx, "whk_nonexistent".into());
        assert_eq!(ctx.db.webhook_subscriptions().iter().count(), 0);
    }

    #[test]
    fn test_webhook_multiple_subscriptions() {
        let ctx = test_ctx();
        create_webhook_subscription(
            &ctx,
            "t".into(),
            "https://a.com".into(),
            "ticket.*".into(),
            "".into(),
        );
        create_webhook_subscription(
            &ctx,
            "t".into(),
            "https://b.com".into(),
            "customer.*".into(),
            "secret".into(),
        );
        create_webhook_subscription(
            &ctx,
            "t".into(),
            "https://c.com".into(),
            "invoice.*".into(),
            "".into(),
        );
        assert_eq!(ctx.db.webhook_subscriptions().iter().count(), 3);
        assert!(ctx.db.webhook_subscriptions().iter().all(|s| s.active));
    }

    #[test]
    fn test_supported_events_contains_expected() {
        assert!(SUPPORTED_EVENTS.contains(&"ticket.created"));
        assert!(SUPPORTED_EVENTS.contains(&"customer.deleted"));
        assert!(SUPPORTED_EVENTS.contains(&"invoice.paid"));
        assert!(SUPPORTED_EVENTS.contains(&"appointment.created"));
        assert_eq!(SUPPORTED_EVENTS.len(), 13);
    }
}
