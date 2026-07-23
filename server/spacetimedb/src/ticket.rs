use spacetimedb::*;

#[spacetimedb::table(accessor = ticket, public)]
#[derive(Debug, Clone)]
pub struct Ticket {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub customer_id: String,
    pub ticket_number: u64,
    pub title: String,
    pub description: String,
    pub device_type: String,
    pub device_model: String,
    pub device_serial: String,
    pub device_imei: String,
    pub device_password: String,
    pub status: String,
    pub priority: String,
    pub assigned_user_id: String,
    pub estimate_id: String,
    pub invoice_id: String,
    pub notes: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::table(accessor = ticket_note, public)]
#[derive(Debug, Clone)]
pub struct TicketNote {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub ticket_id: String,
    pub author: String,
    pub content: String,
    pub internal: bool,
    pub created_at: u64,
}

#[spacetimedb::table(accessor = ticket_timer, public)]
#[derive(Debug, Clone)]
pub struct TicketTimer {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub ticket_id: String,
    pub user_id: String,
    pub start_time: u64,
    pub end_time: u64,
    pub total_seconds: u64,
    pub running: bool,
}

#[spacetimedb::reducer]
pub fn create_ticket(
    ctx: &ReducerContext,
    tenant_id: String,
    customer_id: String,
    title: String,
    description: String,
    device_type: String,
    device_model: String,
    device_serial: String,
    priority: String,
) {
    let id = super::make_id("tkt", ctx);
    let now = super::now_ms(ctx);
    let ticket_number = ctx.db.ticket().iter().count() as u64 + 1001;
    ctx.db.ticket().insert(Ticket {
        id,
        tenant_id,
        customer_id,
        ticket_number,
        title,
        description,
        device_type,
        device_model,
        device_serial,
        device_imei: String::new(),
        device_password: String::new(),
        status: "new".to_string(),
        priority,
        assigned_user_id: String::new(),
        estimate_id: String::new(),
        invoice_id: String::new(),
        notes: String::new(),
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_ticket_status(ctx: &ReducerContext, id: String, status: String) {
    if let Some(t) = ctx.db.ticket().id().find(&id) {
        ctx.db.ticket().id().update(Ticket {
            status,
            updated_at: super::now_ms(ctx),
            ..t
        });
    }
}

#[spacetimedb::reducer]
pub fn assign_ticket(ctx: &ReducerContext, id: String, assigned_user_id: String) {
    if let Some(t) = ctx.db.ticket().id().find(&id) {
        ctx.db.ticket().id().update(Ticket {
            assigned_user_id,
            updated_at: super::now_ms(ctx),
            ..t
        });
    }
}

#[spacetimedb::reducer]
pub fn add_ticket_note(
    ctx: &ReducerContext,
    ticket_id: String,
    author: String,
    content: String,
    internal: bool,
) {
    let id = super::make_id("tnote", ctx);
    // Derive tenant_id from the parent ticket
    let tenant_id = ctx
        .db
        .ticket()
        .id()
        .find(&ticket_id)
        .map_or(String::new(), |t| t.tenant_id.clone());
    ctx.db.ticket_note().insert(TicketNote {
        id,
        tenant_id,
        ticket_id,
        author,
        content,
        internal,
        created_at: super::now_ms(ctx),
    });
}

#[spacetimedb::reducer]
pub fn delete_ticket(ctx: &ReducerContext, id: String) {
    ctx.db.ticket().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn start_ticket_timer(ctx: &ReducerContext, ticket_id: String, user_id: String) {
    let now = super::now_ms(ctx);
    // Stop any existing running timer for this user
    for t in ctx
        .db
        .ticket_timer()
        .iter()
        .filter(|t| t.user_id == user_id && t.running)
    {
        let elapsed = now.saturating_sub(t.start_time) / 1000;
        ctx.db.ticket_timer().id().update(TicketTimer {
            running: false,
            end_time: now,
            total_seconds: t.total_seconds + elapsed,
            ..t
        });
    }
    // Start new timer
    let id = super::make_id("tmr", ctx);
    // Derive tenant_id from the parent ticket
    let tenant_id = ctx
        .db
        .ticket()
        .id()
        .find(&ticket_id)
        .map_or(String::new(), |t| t.tenant_id.clone());
    ctx.db.ticket_timer().insert(TicketTimer {
        id,
        tenant_id,
        ticket_id,
        user_id,
        start_time: now,
        end_time: 0,
        total_seconds: 0,
        running: true,
    });
}

#[spacetimedb::reducer]
pub fn stop_ticket_timer(ctx: &ReducerContext, id: String) {
    let now = super::now_ms(ctx);
    if let Some(t) = ctx.db.ticket_timer().id().find(&id) {
        let elapsed = now.saturating_sub(t.start_time) / 1000;
        ctx.db.ticket_timer().id().update(TicketTimer {
            running: false,
            end_time: now,
            total_seconds: t.total_seconds + elapsed,
            ..t
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_ticket_timer(ctx: &ReducerContext, id: String) {
    ctx.db.ticket_timer().id().delete(&id);
}

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_ticket() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t_tkt".into(),
            "cust_1".into(),
            "Broken phone".into(),
            "Screen is cracked".into(),
            "Phone".into(),
            "iPhone 14".into(),
            "SN12345".into(),
            "high".into(),
        );
        let tickets: Vec<Ticket> = ctx.db.ticket().iter().collect();
        assert_eq!(tickets.len(), 1);
        let t = &tickets[0];
        assert!(t.id.starts_with("tkt_"));
        assert_eq!(t.ticket_number, 1001);
        assert_eq!(t.status, "new");
        assert_eq!(t.priority, "high");
        assert_eq!(t.title, "Broken phone");
        assert_eq!(t.customer_id, "cust_1");
        assert_eq!(t.device_model, "iPhone 14");
        assert_eq!(t.device_serial, "SN12345");
        assert!(t.created_at > 0);
        assert_eq!(t.created_at, t.updated_at);
    }

    #[test]
    fn test_create_second_ticket_increments_number() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t".into(), "c1".into(), "T1".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        create_ticket(&ctx, "t".into(), "c2".into(), "T2".into(), "".into(), "".into(), "".into(), "".into(), "medium".into());
        let tickets: Vec<Ticket> = ctx.db.ticket().iter().collect();
        assert_eq!(tickets.len(), 2);
        let numbers: Vec<u64> = tickets.iter().map(|t| t.ticket_number).collect();
        assert!(numbers.contains(&1001));
        assert!(numbers.contains(&1002));
    }

    #[test]
    fn test_update_ticket_status() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t".into(), "c1".into(), "Test".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        let id = ctx.db.ticket().iter().next().expect("ticket exists").id.clone();
        assert_eq!(ctx.db.ticket().id().find(&id).unwrap().status, "new");
        update_ticket_status(&ctx, id.clone(), "in_progress".into());
        assert_eq!(ctx.db.ticket().id().find(&id).unwrap().status, "in_progress");
    }

    #[test]
    fn test_assign_ticket() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t".into(), "c1".into(), "Assign".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        let id = ctx.db.ticket().iter().next().expect("ticket exists").id.clone();
        assert_eq!(ctx.db.ticket().id().find(&id).unwrap().assigned_user_id, "");
        assign_ticket(&ctx, id.clone(), "user_42".into());
        assert_eq!(ctx.db.ticket().id().find(&id).unwrap().assigned_user_id, "user_42");
    }

    #[test]
    fn test_add_ticket_note() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t".into(), "c1".into(), "Note".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        let ticket_id = ctx.db.ticket().iter().next().expect("ticket exists").id.clone();
        add_ticket_note(&ctx, ticket_id.clone(), "tech_1".into(), "Customer called".into(), false);
        let notes: Vec<TicketNote> = ctx.db.ticket_note().iter().collect();
        assert_eq!(notes.len(), 1);
        assert!(notes[0].id.starts_with("tnote_"));
        assert_eq!(notes[0].ticket_id, ticket_id);
        assert_eq!(notes[0].author, "tech_1");
        assert_eq!(notes[0].content, "Customer called");
        assert!(!notes[0].internal);
    }

    #[test]
    fn test_delete_ticket() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t".into(), "c1".into(), "Del".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        assert_eq!(ctx.db.ticket().iter().count(), 1);
        let id = ctx.db.ticket().iter().next().expect("ticket exists").id.clone();
        delete_ticket(&ctx, id);
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_start_stop_timer() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t".into(), "c1".into(), "Timer".into(), "".into(), "".into(), "".into(), "".into(), "high".into());
        let ticket_id = ctx.db.ticket().iter().next().expect("ticket exists").id.clone();
        start_ticket_timer(&ctx, ticket_id.clone(), "user_1".into());
        let timers: Vec<TicketTimer> = ctx.db.ticket_timer().iter().collect();
        assert_eq!(timers.len(), 1);
        assert!(timers[0].id.starts_with("tmr_"));
        assert!(timers[0].running);
        let timer_id = timers[0].id.clone();
        stop_ticket_timer(&ctx, timer_id.clone());
        let stopped = ctx.db.ticket_timer().id().find(&timer_id).expect("timer exists");
        assert!(!stopped.running);
        assert!(stopped.end_time > 0);
    }

    #[test]
    fn test_start_timer_stops_previous() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t".into(), "c1".into(), "Multi".into(), "".into(), "".into(), "".into(), "".into(), "medium".into());
        let ticket_id = ctx.db.ticket().iter().next().expect("ticket exists").id.clone();
        start_ticket_timer(&ctx, ticket_id.clone(), "user_1".into());
        assert_eq!(ctx.db.ticket_timer().iter().filter(|t| t.running).count(), 1);
        start_ticket_timer(&ctx, ticket_id.clone(), "user_1".into());
        let running: Vec<TicketTimer> = ctx.db.ticket_timer().iter().filter(|t| t.running).collect();
        assert_eq!(running.len(), 1);
        assert_eq!(ctx.db.ticket_timer().iter().count(), 2);
    }

    #[test]
    fn test_delete_ticket_timer() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t".into(), "c1".into(), "DelTmr".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        let ticket_id = ctx.db.ticket().iter().next().expect("ticket exists").id.clone();
        start_ticket_timer(&ctx, ticket_id, "user_1".into());
        assert_eq!(ctx.db.ticket_timer().iter().count(), 1);
        let timer_id = ctx.db.ticket_timer().iter().next().expect("timer exists").id.clone();
        delete_ticket_timer(&ctx, timer_id);
        assert_eq!(ctx.db.ticket_timer().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_ticket() {
        let ctx = test_ctx();
        delete_ticket(&ctx, "tkt_nonexistent".into());
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_update_nonexistent_ticket() {
        let ctx = test_ctx();
        update_ticket_status(&ctx, "tkt_nonexistent".into(), "closed".into());
        assign_ticket(&ctx, "tkt_nonexistent".into(), "user_x".into());
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_stop_nonexistent_timer() {
        let ctx = test_ctx();
        stop_ticket_timer(&ctx, "tmr_nonexistent".into());
        assert_eq!(ctx.db.ticket_timer().iter().count(), 0);
    }

    #[test]
    fn test_create_ticket_defaults() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t".into(), "".into(), "".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        let t = ctx.db.ticket().iter().next().unwrap();
        assert_eq!(t.device_imei, "");
        assert_eq!(t.device_password, "");
        assert_eq!(t.assigned_user_id, "");
        assert_eq!(t.notes, "");
    }
}

