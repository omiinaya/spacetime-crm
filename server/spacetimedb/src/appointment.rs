// TODO (kanban): Replace 10 unwrap() call(s) with proper error handling
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
pub fn create_appointment(
    ctx: &ReducerContext,
    tenant_id: String,
    customer_id: String,
    ticket_id: String,
    title: String,
    description: String,
    start_time: u64,
    end_time: u64,
    all_day: bool,
    series_id: String,
    recurrence_rule: String,
    color: String,
) {
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
        color,
        series_id,
        recurrence_rule,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn set_recurrence(ctx: &ReducerContext, id: String, recurrence_rule: String) {
    if let Some(a) = ctx.db.appointment().id().find(&id) {
        ctx.db.appointment().id().update(Appointment {
            recurrence_rule,
            updated_at: super::now_ms(ctx),
            ..a
        });
    }
}

#[spacetimedb::reducer]
pub fn generate_next_occurrence(
    ctx: &ReducerContext,
    series_id: String,
    start_time: u64,
    end_time: u64,
    recurrence_rule: String,
) {
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
        ctx.db.appointment().id().update(Appointment {
            status,
            updated_at: super::now_ms(ctx),
            ..a
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_appointment(ctx: &ReducerContext, id: String) {
    ctx.db.appointment().id().delete(&id);
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_appointment() {
        let ctx = test_ctx();
        create_appointment(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "Test".into(),
            "desc".into(),
            1000,
            2000,
            false,
            String::new(),
            String::new(),
            String::new(),
        );
        let appts: Vec<Appointment> = ctx.db.appointment().iter().collect();
        assert_eq!(appts.len(), 1);
        let a = &appts[0];
        assert!(a.id.starts_with("appt_"));
        assert_eq!(a.title, "Test");
        assert_eq!(a.status, "scheduled");
        assert_eq!(a.start_time, 1000);
        assert_eq!(a.end_time, 2000);
        assert!(!a.all_day);
        assert!(a.created_at > 0);
        assert_eq!(a.created_at, a.updated_at);
    }

    #[test]
    fn test_create_appointment_with_color_and_series() {
        let ctx = test_ctx();
        create_appointment(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "Color".into(),
            "".into(),
            0,
            0,
            true,
            "series_1".into(),
            "FREQ=WEEKLY".into(),
            "#ff0000".into(),
        );
        let appts: Vec<Appointment> = ctx.db.appointment().iter().collect();
        assert_eq!(appts.len(), 1);
        let a = &appts[0];
        assert_eq!(a.color, "#ff0000");
        assert_eq!(a.series_id, "series_1");
        assert_eq!(a.recurrence_rule, "FREQ=WEEKLY");
        assert!(a.all_day);
    }

    #[test]
    fn test_update_appointment_status() {
        let ctx = test_ctx();
        create_appointment(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "Status".into(),
            "".into(),
            0,
            0,
            false,
            "".into(),
            "".into(),
            "".into(),
        );
        let id = ctx.db.appointment().iter().next().unwrap().id.clone();
        assert_eq!(
            ctx.db.appointment().id().find(&id).unwrap().status,
            "scheduled"
        );
        update_appointment_status(&ctx, id.clone(), "completed".into());
        assert_eq!(
            ctx.db.appointment().id().find(&id).unwrap().status,
            "completed"
        );
        update_appointment_status(&ctx, id.clone(), "cancelled".into());
        assert_eq!(
            ctx.db.appointment().id().find(&id).unwrap().status,
            "cancelled"
        );
    }

    #[test]
    fn test_update_nonexistent_appointment_doesnt_panic() {
        let ctx = test_ctx();
        update_appointment_status(&ctx, "appt_nonexistent".into(), "completed".into());
        assert_eq!(ctx.db.appointment().iter().count(), 0);
    }

    #[test]
    fn test_set_recurrence() {
        let ctx = test_ctx();
        create_appointment(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "Recur".into(),
            "".into(),
            0,
            0,
            false,
            "".into(),
            "".into(),
            "".into(),
        );
        let id = ctx.db.appointment().iter().next().unwrap().id.clone();
        assert!(ctx
            .db
            .appointment()
            .id()
            .find(&id)
            .unwrap()
            .recurrence_rule
            .is_empty());
        let rule = "FREQ=WEEKLY;BYDAY=MO";
        set_recurrence(&ctx, id.clone(), rule.into());
        assert_eq!(
            ctx.db.appointment().id().find(&id).unwrap().recurrence_rule,
            rule
        );
    }

    #[test]
    fn test_set_recurrence_nonexistent() {
        let ctx = test_ctx();
        set_recurrence(&ctx, "appt_nonexistent".into(), "FREQ=DAILY".into());
        assert_eq!(ctx.db.appointment().iter().count(), 0);
    }

    #[test]
    fn test_generate_next_occurrence() {
        let ctx = test_ctx();
        create_appointment(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "Series".into(),
            "".into(),
            1000,
            2000,
            false,
            "".into(),
            "FREQ=WEEKLY".into(),
            "".into(),
        );
        let parent = ctx.db.appointment().iter().next().unwrap();
        let series_id = parent.id.clone();
        assert_eq!(ctx.db.appointment().iter().count(), 1);
        generate_next_occurrence(&ctx, series_id.clone(), 2000, 3000, "FREQ=WEEKLY".into());
        assert_eq!(ctx.db.appointment().iter().count(), 2);
        let child = ctx
            .db
            .appointment()
            .iter()
            .find(|a| a.id != series_id)
            .unwrap();
        assert_eq!(child.title, "Series");
        assert_eq!(child.status, "scheduled");
        assert_eq!(child.start_time, 2000);
        assert_eq!(child.end_time, 3000);
        assert_eq!(child.series_id, series_id);
    }

    #[test]
    fn test_generate_next_occurrence_no_parent() {
        let ctx = test_ctx();
        generate_next_occurrence(
            &ctx,
            "appt_nonexistent".into(),
            1000,
            2000,
            "FREQ=DAILY".into(),
        );
        assert_eq!(ctx.db.appointment().iter().count(), 0);
    }

    #[test]
    fn test_delete_appointment() {
        let ctx = test_ctx();
        create_appointment(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "Del".into(),
            "".into(),
            0,
            0,
            false,
            "".into(),
            "".into(),
            "".into(),
        );
        assert_eq!(ctx.db.appointment().iter().count(), 1);
        let id = ctx.db.appointment().iter().next().unwrap().id.clone();
        delete_appointment(&ctx, id);
        assert_eq!(ctx.db.appointment().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_appointment() {
        let ctx = test_ctx();
        delete_appointment(&ctx, "appt_nonexistent".into());
        assert_eq!(ctx.db.appointment().iter().count(), 0);
    }

    #[test]
    fn test_tenant_isolation() {
        let ctx = test_ctx();
        create_appointment(
            &ctx,
            "t_a".into(),
            "c1".into(),
            "".into(),
            "A".into(),
            "".into(),
            0,
            0,
            false,
            "".into(),
            "".into(),
            "".into(),
        );
        create_appointment(
            &ctx,
            "t_b".into(),
            "c2".into(),
            "".into(),
            "B".into(),
            "".into(),
            0,
            0,
            false,
            "".into(),
            "".into(),
            "".into(),
        );
        let a_only: Vec<Appointment> = ctx
            .db
            .appointment()
            .iter()
            .filter(|a| a.tenant_id == "t_a")
            .collect();
        assert_eq!(a_only.len(), 1);
        assert_eq!(a_only[0].title, "A");
    }
}
