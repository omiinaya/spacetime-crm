use spacetimedb::*;

#[spacetimedb::table(accessor = gift_cards, public)]
#[derive(Debug, Clone)]
pub struct GiftCard {
    #[primary_key]
    pub id: String,
    pub code: String,
    pub tenant_id: String,
    pub customer_id: String,
    pub customer_name: String,
    pub initial_balance: f64,
    pub remaining_balance: f64,
    pub created_by: String,
    pub created_at: u64,
    pub expires_at: u64,        // 0 = never expires
    pub notes: String,
    pub active: bool,
}

#[spacetimedb::reducer]
pub fn create_gift_card(
    ctx: &ReducerContext,
    code: String,
    tenant_id: String,
    customer_id: String,
    customer_name: String,
    initial_balance: f64,
    created_by: String,
    expires_at: u64,
    notes: String,
) {
    let id = super::make_id("gift", ctx);
    ctx.db.gift_cards().insert(GiftCard {
        id,
        code,
        tenant_id,
        customer_id,
        customer_name,
        initial_balance,
        remaining_balance: initial_balance,
        created_by,
        created_at: super::now_ms(ctx),
        expires_at,
        notes,
        active: true,
    });
}

#[spacetimedb::reducer]
pub fn redeem_gift_card(ctx: &ReducerContext, id: String, amount: f64) {
    if let Some(mut card) = ctx.db.gift_cards().id().find(&id) {
        card.remaining_balance -= amount;
        if card.remaining_balance <= 0.0 {
            card.remaining_balance = 0.0;
            card.active = false;
        }
        ctx.db.gift_cards().id().update(card);
    }
}

#[spacetimedb::reducer]
pub fn void_gift_card(ctx: &ReducerContext, id: String) {
    if let Some(mut card) = ctx.db.gift_cards().id().find(&id) {
        card.active = false;
        ctx.db.gift_cards().id().update(card);
    }
}
