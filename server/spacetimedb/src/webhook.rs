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

pub(crate) fn now_ms(ctx: &ReducerContext) -> u64 {
    ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000
}

pub(crate) fn make_webhook_id(ctx: &ReducerContext) -> String {
    let ts = now_ms(ctx);
    let discrim = ctx.sender().to_hex();
    let short = if discrim.len() > 8 {
        &discrim[..8]
    } else {
        &discrim
    };
    format!("whk_{}_{}", ts, short)
}
