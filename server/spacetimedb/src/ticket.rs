// TODO (kanban): Replace 13 unwrap() call(s) with proper error handling
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
    device_imei: String,
    device_password: String,
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
        device_imei,
        device_password,
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
            "t".into(),
            "c1".into(),
            "Broken".into(),
            "Cracked".into(),
            "iPhone".into(),
            "15".into(),
            "SN001".into(),
            String::new(),
            String::new(),
            "high".into(),
        );
        let tickets: Vec<Ticket> = ctx.db.ticket().iter().collect();
        assert_eq!(tickets.len(), 1);
        let t = &tickets[0];
        assert!(t.id.starts_with("tkt_"));
        assert_eq!(t.title, "Broken");
        assert_eq!(t.status, "new");
        assert_eq!(t.priority, "high");
        assert_eq!(t.device_type, "iPhone");
        assert_eq!(t.device_model, "15");
        assert_eq!(t.device_serial, "SN001");
        assert!(t.created_at > 0);
        assert_eq!(t.created_at, t.updated_at);
        assert!(t.ticket_number > 0);
    }

    #[test]
    fn test_update_ticket_status() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Fix".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            "low".into(),
        );
        let t = ctx.db.ticket().iter().next().unwrap();
        let id = t.id.clone();
        assert_eq!(t.status, "new");
        update_ticket_status(&ctx, id.clone(), "in_progress".into());
        assert_eq!(
            ctx.db.ticket().id().find(&id).unwrap().status,
            "in_progress"
        );
        update_ticket_status(&ctx, id.clone(), "resolved".into());
        assert_eq!(ctx.db.ticket().id().find(&id).unwrap().status, "resolved");
    }

    #[test]
    fn test_update_nonexistent_ticket() {
        let ctx = test_ctx();
        update_ticket_status(&ctx, "tkt_nope".into(), "resolved".into());
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_assign_ticket() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Assign".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            "medium".into(),
        );
        let t = ctx.db.ticket().iter().next().unwrap();
        let id = t.id.clone();
        assert!(t.assigned_user_id.is_empty());
        assign_ticket(&ctx, id.clone(), "user_tech".into());
        assert_eq!(
            ctx.db.ticket().id().find(&id).unwrap().assigned_user_id,
            "user_tech"
        );
    }

    #[test]
    fn test_assign_nonexistent_ticket() {
        let ctx = test_ctx();
        assign_ticket(&ctx, "tkt_nope".into(), "user_x".into());
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_add_ticket_note() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Note".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            "low".into(),
        );
        let t = ctx.db.ticket().iter().next().unwrap();
        let tid = t.id.clone();
        add_ticket_note(
            &ctx,
            tid.clone(),
            "Bob".into(),
            "Checked device".into(),
            false,
        );
        let notes: Vec<TicketNote> = ctx.db.ticket_note().iter().collect();
        assert_eq!(notes.len(), 1);
        let n = &notes[0];
        assert!(n.id.starts_with("tnote_"));
        assert_eq!(n.ticket_id, tid);
        assert_eq!(n.author, "Bob");
        assert_eq!(n.content, "Checked device");
        assert!(!n.internal);
        assert!(n.created_at > 0);
    }

    #[test]
    fn test_add_internal_ticket_note() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Int".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            "low".into(),
        );
        let tid = ctx.db.ticket().iter().next().unwrap().id.clone();
        add_ticket_note(&ctx, tid, "Tech".into(), "Internal note".into(), true);
        let n = ctx.db.ticket_note().iter().next().unwrap();
        assert!(n.internal);
    }

    #[test]
    fn test_delete_ticket() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Del".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            "low".into(),
        );
        assert_eq!(ctx.db.ticket().iter().count(), 1);
        let id = ctx.db.ticket().iter().next().unwrap().id.clone();
        delete_ticket(&ctx, id);
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_ticket() {
        let ctx = test_ctx();
        delete_ticket(&ctx, "tkt_nope".into());
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_ticket_timer_lifecycle() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Timer".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            "low".into(),
        );
        let tid = ctx.db.ticket().iter().next().unwrap().id.clone();
        start_ticket_timer(&ctx, tid.clone(), "user_1".into());
        let timers: Vec<TicketTimer> = ctx.db.ticket_timer().iter().collect();
        assert_eq!(timers.len(), 1);
        let tmr = &timers[0];
        assert!(tmr.running);
        assert_eq!(tmr.user_id, "user_1");
        assert_eq!(tmr.ticket_id, tid);
        stop_ticket_timer(&ctx, tmr.id.clone());
        let stopped = ctx.db.ticket_timer().id().find(&tmr.id).unwrap();
        assert!(!stopped.running);
        assert!(stopped.end_time > 0);
    }

    #[test]
    fn test_delete_ticket_timer() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Del timer".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            "low".into(),
        );
        let tid = ctx.db.ticket().iter().next().unwrap().id.clone();
        start_ticket_timer(&ctx, tid, "u".into());
        assert_eq!(ctx.db.ticket_timer().iter().count(), 1);
        let tid2 = ctx.db.ticket_timer().iter().next().unwrap().id.clone();
        delete_ticket_timer(&ctx, tid2);
        assert_eq!(ctx.db.ticket_timer().iter().count(), 0);
    }

    #[test]
    fn test_tenant_isolation() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t_a".into(),
            "c1".into(),
            "A".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            "low".into(),
        );
        create_ticket(
            &ctx,
            "t_b".into(),
            "c2".into(),
            "B".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            "high".into(),
        );
        let a_only: Vec<Ticket> = ctx
            .db
            .ticket()
            .iter()
            .filter(|t| t.tenant_id == "t_a")
            .collect();
        assert_eq!(a_only.len(), 1);
        assert_eq!(a_only[0].title, "A");
    }
}
