// TODO (kanban): Replace 14 unwrap() call(s) with proper error handling
// TODO (kanban): Replace 14 unwrap() call(s) with proper error handling
use spacetimedb::*;

/// Tests for gift card reducers — create, redeem, void.
#[cfg(test)]
mod tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_create_gift_card() {
        let ctx = test_ctx();

        create_gift_card(
            &ctx,
            "GC-TEST-001".into(),
            "tenant_1".into(),
            "cust_1".into(),
            "Alice".into(),
            100.0,
            "user_1".into(),
            0, // no expiry
            "".into(),
        );

        let cards: Vec<GiftCard> = ctx.db.gift_cards().iter().collect();
        assert_eq!(cards.len(), 1);
        let card = &cards[0];

        assert!(card.id.starts_with("gift_"));
        assert_eq!(card.code, "GC-TEST-001");
        assert_eq!(card.initial_balance, 100.0);
        assert_eq!(card.remaining_balance, 100.0);
        assert!(card.active);
        assert_eq!(card.customer_name, "Alice");
        assert_eq!(card.created_by, "user_1");
        assert!(card.created_at > 0);
    }

    #[test]
    fn test_create_multiple_gift_cards() {
        let ctx = test_ctx();

        create_gift_card(
            &ctx,
            "GC-AAA".into(),
            "t1".into(),
            "".into(),
            "A".into(),
            50.0,
            "u1".into(),
            0,
            "".into(),
        );
        create_gift_card(
            &ctx,
            "GC-BBB".into(),
            "t1".into(),
            "".into(),
            "B".into(),
            75.0,
            "u1".into(),
            0,
            "notes".into(),
        );

        let cards: Vec<GiftCard> = ctx.db.gift_cards().iter().collect();
        assert_eq!(cards.len(), 2);

        let codes: Vec<&str> = cards.iter().map(|c| c.code.as_str()).collect();
        assert!(codes.contains(&"GC-AAA"));
        assert!(codes.contains(&"GC-BBB"));
    }

    #[test]
    fn test_redeem_gift_card_partial() {
        let ctx = test_ctx();

        create_gift_card(
            &ctx,
            "GC-REDEEM".into(),
            "t1".into(),
            "".into(),
            "Bob".into(),
            100.0,
            "u1".into(),
            0,
            "".into(),
        );

        let card_id = ctx.db.gift_cards().iter().next().unwrap().id.clone();
        let result = redeem_gift_card(&ctx, card_id.clone(), 30.0);
        assert!(result.is_ok());

        let card = ctx.db.gift_cards().id().find(&card_id).unwrap();
        assert_eq!(card.remaining_balance, 70.0);
        assert!(card.active); // Still has balance
    }

    #[test]
    fn test_redeem_gift_card_full() {
        let ctx = test_ctx();

        create_gift_card(
            &ctx,
            "GC-FULL".into(),
            "t1".into(),
            "".into(),
            "Carol".into(),
            50.0,
            "u1".into(),
            0,
            "".into(),
        );

        let card_id = ctx.db.gift_cards().iter().next().unwrap().id.clone();
        let result = redeem_gift_card(&ctx, card_id.clone(), 50.0);
        assert!(result.is_ok());

        let card = ctx.db.gift_cards().id().find(&card_id).unwrap();
        assert_eq!(card.remaining_balance, 0.0);
        assert!(!card.active); // Exhausted — automatically voided
    }

    #[test]
    fn test_redeem_gift_card_over() {
        let ctx = test_ctx();

        create_gift_card(
            &ctx,
            "GC-OVER".into(),
            "t1".into(),
            "".into(),
            "Dave".into(),
            25.0,
            "u1".into(),
            0,
            "".into(),
        );

        let card_id = ctx.db.gift_cards().iter().next().unwrap().id.clone();
        let result = redeem_gift_card(&ctx, card_id.clone(), 40.0);
        assert!(result.is_err()); // Over-redemption is rejected atomically

        let card = ctx.db.gift_cards().id().find(&card_id).unwrap();
        assert_eq!(card.remaining_balance, 25.0); // Unchanged
        assert!(card.active); // Still usable
    }

    #[test]
    fn test_redeem_nonexistent_card() {
        let ctx = test_ctx();
        // Should return an error, not panic
        let result = redeem_gift_card(&ctx, "non_existent_id".into(), 10.0);
        assert!(result.is_err());
        let cards: Vec<GiftCard> = ctx.db.gift_cards().iter().collect();
        assert_eq!(cards.len(), 0);
    }

    #[test]
    fn test_redeem_inactive_card_rejected() {
        let ctx = test_ctx();

        create_gift_card(
            &ctx,
            "GC-INACTIVE".into(),
            "t1".into(),
            "".into(),
            "Mallory".into(),
            50.0,
            "u1".into(),
            0,
            "".into(),
        );

        let card_id = ctx.db.gift_cards().iter().next().unwrap().id.clone();
        void_gift_card(&ctx, card_id.clone());
        let result = redeem_gift_card(&ctx, card_id.clone(), 10.0);
        assert!(result.is_err()); // Voided card cannot be redeemed
        let card = ctx.db.gift_cards().id().find(&card_id).unwrap();
        assert_eq!(card.remaining_balance, 50.0); // Unchanged
        assert!(!card.active);
    }

    #[test]
    fn test_void_gift_card() {
        let ctx = test_ctx();

        create_gift_card(
            &ctx,
            "GC-VOID".into(),
            "t1".into(),
            "".into(),
            "Eve".into(),
            200.0,
            "u1".into(),
            0,
            "".into(),
        );

        let card_id = ctx.db.gift_cards().iter().next().unwrap().id.clone();
        void_gift_card(&ctx, card_id.clone());

        let card = ctx.db.gift_cards().id().find(&card_id).unwrap();
        assert!(!card.active); // Voided
        assert_eq!(card.remaining_balance, 200.0); // Balance preserved
    }

    #[test]
    fn test_void_nonexistent_card() {
        let ctx = test_ctx();
        // Should not panic
        void_gift_card(&ctx, "ghost_id".into());
    }

    #[test]
    fn test_void_already_voided_card() {
        let ctx = test_ctx();

        create_gift_card(
            &ctx,
            "GC-DBL".into(),
            "t1".into(),
            "".into(),
            "Frank".into(),
            10.0,
            "u1".into(),
            0,
            "".into(),
        );

        let card_id = ctx.db.gift_cards().iter().next().unwrap().id.clone();
        void_gift_card(&ctx, card_id.clone());
        void_gift_card(&ctx, card_id.clone()); // Double void

        let card = ctx.db.gift_cards().id().find(&card_id).unwrap();
        assert!(!card.active); // Still voided
    }

    #[test]
    fn test_gift_card_initial_balance_matches_remaining() {
        let ctx = test_ctx();

        create_gift_card(
            &ctx,
            "GC-BAL".into(),
            "t1".into(),
            "".into(),
            "Grace".into(),
            150.0,
            "u1".into(),
            0,
            "".into(),
        );

        let card = ctx.db.gift_cards().iter().next().unwrap();
        assert_eq!(card.initial_balance, card.remaining_balance);
        assert_eq!(card.initial_balance, 150.0);
    }

    #[test]
    fn test_gift_card_expiry_field() {
        let ctx = test_ctx();
        let future_ts: u64 = 1893456000000; // 2030-01-01

        create_gift_card(
            &ctx,
            "GC-EXP".into(),
            "t1".into(),
            "".into(),
            "Heidi".into(),
            50.0,
            "u1".into(),
            future_ts,
            "has expiry".into(),
        );

        let card = ctx.db.gift_cards().iter().next().unwrap();
        assert_eq!(card.expires_at, future_ts);
        assert_eq!(card.notes, "has expiry");
        assert!(card.active);
    }
}

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
    pub expires_at: u64, // 0 = never expires
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
pub fn redeem_gift_card(ctx: &ReducerContext, id: String, amount: f64) -> Result<(), String> {
    if let Some(mut card) = ctx.db.gift_cards().id().find(&id) {
        if !card.active {
            return Err("Gift card is no longer active".to_string());
        }
        if amount <= 0.0 {
            return Err("Redemption amount must be positive".to_string());
        }
        if amount > card.remaining_balance {
            return Err("Insufficient balance on gift card".to_string());
        }
        card.remaining_balance -= amount;
        if card.remaining_balance <= 0.0 {
            card.remaining_balance = 0.0;
            card.active = false;
        }
        ctx.db.gift_cards().id().update(card);
        Ok(())
    } else {
        Err("Gift card not found".to_string())
    }
}

#[spacetimedb::reducer]
pub fn void_gift_card(ctx: &ReducerContext, id: String) {
    if let Some(mut card) = ctx.db.gift_cards().id().find(&id) {
        card.active = false;
        ctx.db.gift_cards().id().update(card);
    }
}
