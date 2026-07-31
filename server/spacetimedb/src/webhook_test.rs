
#[cfg(test)]
mod tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_webhook_subscription() {
        let ctx = test_ctx();
        create_webhook_subscription(
            &ctx,
            "t_1".into(),
            "https://hooks.example.com/callback".into(),
            "ticket.created,ticket.updated".into(),
            "hmac_secret".into(),
        );
        let subs: Vec<WebhookSubscription> = ctx.db.webhook_subscriptions().iter().collect();
        assert_eq!(subs.len(), 1);
        let s = &subs[0];
        assert!(s.id.starts_with("whk_"));
        assert_eq!(s.url, "https://hooks.example.com/callback");
        assert_eq!(s.events, "ticket.created,ticket.updated");
        assert_eq!(s.secret, "hmac_secret");
        assert!(s.active);
    }

    #[test]
    fn test_update_webhook_subscription() {
        let ctx = test_ctx();
        create_webhook_subscription(
            &ctx,
            "t_1".into(),
            "https://old.url".into(),
            "ticket.created".into(),
            "old_secret".into(),
        );
        let id = ctx
            .db
            .webhook_subscriptions()
            .iter()
            .next()
            .expect("expected sub")
            .id
            .clone();
        update_webhook_subscription(
            &ctx,
            id.clone(),
            "https://new.url".into(),
            "ticket.updated".into(),
            "new_secret".into(),
            false,
        );
        let updated = ctx
            .db
            .webhook_subscriptions()
            .id()
            .find(&id)
            .expect("expected to exist");
        assert_eq!(updated.url, "https://new.url");
        assert_eq!(updated.events, "ticket.updated");
        assert_eq!(updated.secret, "new_secret");
        assert!(!updated.active);
    }

    #[test]
    fn test_delete_webhook_subscription() {
        let ctx = test_ctx();
        create_webhook_subscription(
            &ctx,
            "t_1".into(),
            "https://del.url".into(),
            "ticket.created".into(),
            "".into(),
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
    fn test_update_nonexistent_webhook() {
        let ctx = test_ctx();
        update_webhook_subscription(
            &ctx,
            "whk_nonexistent".into(),
            "url".into(),
            "evt".into(),
            "sec".into(),
            true,
        );
        assert_eq!(ctx.db.webhook_subscriptions().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_webhook() {
        let ctx = test_ctx();
        delete_webhook_subscription(&ctx, "whk_nonexistent".into());
        assert_eq!(ctx.db.webhook_subscriptions().iter().count(), 0);
    }

    #[test]
    fn test_supported_events_are_defined() {
        assert!(SUPPORTED_EVENTS.contains(&"customer.created"));
        assert!(SUPPORTED_EVENTS.contains(&"ticket.created"));
        assert!(SUPPORTED_EVENTS.contains(&"invoice.created"));
        assert!(SUPPORTED_EVENTS.contains(&"payment.created"));
        assert!(SUPPORTED_EVENTS.contains(&"appointment.created"));
        assert_eq!(SUPPORTED_EVENTS.len(), 13);
    }

    #[test]
    fn test_now_ms_returns_positive() {
        let ctx = test_ctx();
        let t = now_ms(&ctx);
        assert!(t > 0, "timestamp should be positive");
    }

    #[test]
    fn test_make_webhook_id_format() {
        let ctx = test_ctx();
        let id = make_webhook_id(&ctx);
        assert!(id.starts_with("whk_"), "id should start with whk_");
        assert!(id.len() > 10, "id should have reasonable length");
    }
}
