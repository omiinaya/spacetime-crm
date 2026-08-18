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
    device_imei: String,
    device_password: String,
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
        ctx.db.ticket().id().update(Ticket { status, updated_at: super::now_ms(ctx), ..t });
    }
}

#[spacetimedb::reducer]
pub fn assign_ticket(ctx: &ReducerContext, id: String, assigned_user_id: String) {
    if let Some(t) = ctx.db.ticket().id().find(&id) {
        ctx.db.ticket().id().update(Ticket { assigned_user_id, updated_at: super::now_ms(ctx), ..t });
    }
}

#[spacetimedb::reducer]
pub fn add_ticket_note(ctx: &ReducerContext, ticket_id: String, author: String, content: String, internal: bool) {
    let id = super::make_id("tnote", ctx);
    // Derive tenant_id from the parent ticket
    let tenant_id = ctx.db.ticket().id().find(&ticket_id).map_or(String::new(), |t| t.tenant_id.clone());
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
    for t in ctx.db.ticket_timer().iter().filter(|t| t.user_id == user_id && t.running) {
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
    let tenant_id = ctx.db.ticket().id().find(&ticket_id).map_or(String::new(), |t| t.tenant_id.clone());
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
