use spacetimedb::*;

#[spacetimedb::table(accessor = appointment, public)]
#[derive(Debug, Clone)]
pub struct Appointment {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub customer_id: String,
    pub ticket_id: String,
    pub title: String,
    pub description: String,
    pub start_time: u64,
    pub end_time: u64,
    pub all_day: bool,
    pub status: String,
    pub color: String,
    pub series_id: String,
    pub recurrence_rule: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn create_appointment(ctx: &ReducerContext, tenant_id: String, customer_id: String, ticket_id: String, title: String, description: String, start_time: u64, end_time: u64, all_day: bool, series_id: String, recurrence_rule: String) {
    let id = super::make_id("appt", ctx);
    let now = super::now_ms(ctx);
    ctx.db.appointment().insert(Appointment {
        id,
        tenant_id,
        customer_id,
        ticket_id,
        title,
        description,
        start_time,
        end_time,
        all_day,
        status: "scheduled".to_string(),
        color: String::new(),
        series_id,
        recurrence_rule,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn set_recurrence(ctx: &ReducerContext, id: String, recurrence_rule: String) {
    if let Some(a) = ctx.db.appointment().id().find(&id) {
        ctx.db.appointment().id().update(Appointment { recurrence_rule, updated_at: super::now_ms(ctx), ..a });
    }
}

#[spacetimedb::reducer]
pub fn generate_next_occurrence(ctx: &ReducerContext, series_id: String, start_time: u64, end_time: u64, recurrence_rule: String) {
    let id = super::make_id("appt", ctx);
    let now = super::now_ms(ctx);
    if let Some(parent) = ctx.db.appointment().id().find(&series_id) {
        ctx.db.appointment().insert(Appointment {
            id,
            tenant_id: parent.tenant_id.clone(),
            customer_id: parent.customer_id.clone(),
            ticket_id: parent.ticket_id.clone(),
            title: parent.title.clone(),
            description: parent.description.clone(),
            start_time,
            end_time,
            all_day: parent.all_day,
            status: "scheduled".to_string(),
            color: parent.color.clone(),
            series_id: series_id.clone(),
            recurrence_rule,
            created_at: now,
            updated_at: now,
        });
    }
}

#[spacetimedb::reducer]
pub fn update_appointment_status(ctx: &ReducerContext, id: String, status: String) {
    if let Some(a) = ctx.db.appointment().id().find(&id) {
        ctx.db.appointment().id().update(Appointment { status, updated_at: super::now_ms(ctx), ..a });
    }
}

#[spacetimedb::reducer]
pub fn delete_appointment(ctx: &ReducerContext, id: String) {
    ctx.db.appointment().id().delete(&id);
}
