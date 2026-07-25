use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_scheduled_report() {
        let ctx = test_ctx();
        create_scheduled_report(
            &ctx,
            "t_sr".into(),
            "Weekly Summary".into(),
            "revenue".into(),
            "weekly".into(),
            r#"{"day":"Mon"}"#.into(),
            r#"["alice@test.com"]"#.into(),
            r#"{"tenant_id":"t_sr"}"#.into(),
            1700000000000,
        );
        let reports: Vec<ScheduledReport> = ctx.db.scheduled_reports().iter().collect();
        assert_eq!(reports.len(), 1);
        let r = &reports[0];
        assert!(r.id.starts_with("srpt_"));
        assert_eq!(r.name, "Weekly Summary");
        assert!(r.enabled);
    }

    #[test]
    fn test_update_scheduled_report() {
        let ctx = test_ctx();
        create_scheduled_report(
            &ctx,
            "t".into(),
            "Old".into(),
            "rev".into(),
            "d".into(),
            "{}".into(),
            "[]".into(),
            "{}".into(),
            1000,
        );
        let id = ctx
            .db
            .scheduled_reports()
            .iter()
            .next()
            .expect("expected at least one scheduled_reports record")
            .id
            .clone();
        update_scheduled_report(
            &ctx,
            id.clone(),
            "New Name".into(),
            "expenses".into(),
            "monthly".into(),
            r#"{"day":1}"#.into(),
            r#"["b@t.com"]"#.into(),
            r#"{"x":1}"#.into(),
            2000,
            false,
        );
        let updated = ctx
            .db
            .scheduled_reports()
            .id()
            .find(&id)
            .expect("expected record to exist");
        assert_eq!(updated.name, "New Name");
        assert_eq!(updated.report_type, "expenses");
        assert!(!updated.enabled);
    }

    #[test]
    fn test_delete_scheduled_report() {
        let ctx = test_ctx();
        create_scheduled_report(
            &ctx,
            "t".into(),
            "Del".into(),
            "r".into(),
            "d".into(),
            "{}".into(),
            "[]".into(),
            "{}".into(),
            1000,
        );
        assert_eq!(ctx.db.scheduled_reports().iter().count(), 1);
        let id = ctx
            .db
            .scheduled_reports()
            .iter()
            .next()
            .expect("expected at least one scheduled_reports record")
            .id
            .clone();
        delete_scheduled_report(&ctx, id);
        assert_eq!(ctx.db.scheduled_reports().iter().count(), 0);
    }

    #[test]
    fn test_mark_report_run() {
        let ctx = test_ctx();
        create_scheduled_report(
            &ctx,
            "t".into(),
            "R".into(),
            "r".into(),
            "d".into(),
            "{}".into(),
            "[]".into(),
            "{}".into(),
            1000,
        );
        let id = ctx
            .db
            .scheduled_reports()
            .iter()
            .next()
            .expect("expected at least one scheduled_reports record")
            .id
            .clone();
        assert_eq!(
            ctx.db
                .scheduled_reports()
                .id()
                .find(&id)
                .expect("expected record to exist")
                .last_run_at,
            0
        );
        mark_report_run(&ctx, id.clone(), 2000);
        let updated = ctx
            .db
            .scheduled_reports()
            .id()
            .find(&id)
            .expect("expected record to exist");
        assert!(updated.last_run_at > 0);
        assert_eq!(updated.next_run_at, 2000);
    }

    #[test]
    fn test_mark_report_error() {
        let ctx = test_ctx();
        create_scheduled_report(
            &ctx,
            "t".into(),
            "Err".into(),
            "r".into(),
            "d".into(),
            "{}".into(),
            "[]".into(),
            "{}".into(),
            1000,
        );
        let id = ctx
            .db
            .scheduled_reports()
            .iter()
            .next()
            .expect("expected at least one scheduled_reports record")
            .id
            .clone();
        assert!(ctx
            .db
            .scheduled_reports()
            .id()
            .find(&id)
            .expect("expected record to exist")
            .last_error
            .is_empty());
        mark_report_error(&ctx, id.clone(), "API timeout".into());
        assert_eq!(
            ctx.db
                .scheduled_reports()
                .id()
                .find(&id)
                .expect("expected record to exist")
                .last_error,
            "API timeout"
        );
    }
}
