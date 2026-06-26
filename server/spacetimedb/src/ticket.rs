use spacetimedb::*;

#[spacetimedb::table(accessor = ticket, public)]
#[derive(Debug, Clone)]
pub struct Ticket {
    #[primary_key]
    pub id: String,
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
    ctx.db.ticket_note().insert(TicketNote {
        id,
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
