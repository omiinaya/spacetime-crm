use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::appointment::appointment;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_appointment() {
        let ctx = test_ctx();
        create_appointment(
            &ctx,
            "t_appt".into(),
            "cust_1".into(),
            "tkt_1".into(),
            "Screen repair".into(),
            "Replace cracked screen".into(),
            1700000000000,
            1700003600000,
            false,
            String::new(),
            String::new(),
        );
        let appts: Vec<Appointment> = ctx.db.appointment().iter().collect();
        assert_eq!(appts.len(), 1);
        let a = &appts[0];
        assert!(a.id.starts_with("appt_"));
        assert_eq!(a.title, "Screen repair");
        assert_eq!(a.status, "scheduled");
        assert_eq!(a.start_time, 1700000000000);
        assert_eq!(a.end_time, 1700003600000);
        assert!(!a.all_day);
        assert!(a.created_at > 0);
        assert_eq!(a.created_at, a.updated_at);
    }

    #[test]
    fn test_update_appointment_status() {
        let ctx = test_ctx();
        create_appointment(
            &ctx,
            "t".into(),
            "c1".into(),
            "".into(),
            "Test".into(),
            "".into(),
            1000,
            2000,
            false,
            "".into(),
            "".into(),
        );
        let a = ctx
            .db
            .appointment()
            .iter()
            .next()
            .expect("expected at least one appointment record");
        assert_eq!(a.status, "scheduled");
        let id = a.id.clone();
        update_appointment_status(&ctx, id.clone(), "completed".into());
        let updated = ctx
            .db
            .appointment()
            .id()
            .find(&id)
            .expect("expected record to exist");
        assert_eq!(updated.status, "completed");
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
            1000,
            2000,
            false,
            "".into(),
            "".into(),
        );
        let a = ctx
            .db
            .appointment()
            .iter()
            .next()
            .expect("expected at least one appointment record");
        let id = a.id.clone();
        assert!(a.recurrence_rule.is_empty());
        let rule = "FREQ=WEEKLY;BYDAY=MO";
        set_recurrence(&ctx, id.clone(), rule.into());
        let updated = ctx
            .db
            .appointment()
            .id()
            .find(&id)
            .expect("expected record to exist");
        assert_eq!(updated.recurrence_rule, rule);
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
        );
        let parent = ctx
            .db
            .appointment()
            .iter()
            .next()
            .expect("expected at least one appointment record");
        let series_id = parent.id.clone();
        assert_eq!(ctx.db.appointment().iter().count(), 1);
        generate_next_occurrence(&ctx, series_id.clone(), 2000, 3000, "FREQ=WEEKLY".into());
        assert_eq!(ctx.db.appointment().iter().count(), 2);
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
            1000,
            2000,
            false,
            "".into(),
            "".into(),
        );
        assert_eq!(ctx.db.appointment().iter().count(), 1);
        let id = ctx
            .db
            .appointment()
            .iter()
            .next()
            .expect("expected at least one appointment record")
            .id
            .clone();
        delete_appointment(&ctx, id);
        assert_eq!(ctx.db.appointment().iter().count(), 0);
    }

    #[test]
    fn test_update_nonexistent_appointment_doesnt_panic() {
        let ctx = test_ctx();
        update_appointment_status(&ctx, "appt_nonexistent".into(), "completed".into());
        assert_eq!(ctx.db.appointment().iter().count(), 0);
    }
}
