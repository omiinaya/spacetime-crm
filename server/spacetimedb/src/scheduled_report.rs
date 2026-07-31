use spacetimedb::*;

#[spacetimedb::table(accessor = scheduled_reports, public)]
#[derive(Debug, Clone)]
pub struct ScheduledReport {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub name: String,
    pub report_type: String,
    pub schedule_frequency: String,
    pub schedule_config_json: String,
    pub recipients_json: String,
    pub filters_json: String,
    pub next_run_at: u64,
    pub last_run_at: u64,
    pub last_error: String,
    pub enabled: bool,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn create_scheduled_report(
    ctx: &ReducerContext,
    tenant_id: String,
    name: String,
    report_type: String,
    schedule_frequency: String,
    schedule_config_json: String,
    recipients_json: String,
    filters_json: String,
    next_run_at: u64,
) {
    let id = super::make_id("srpt", ctx);
    let now = super::now_ms(ctx);
    ctx.db.scheduled_reports().insert(ScheduledReport {
        id,
        tenant_id,
        name,
        report_type,
        schedule_frequency,
        schedule_config_json,
        recipients_json,
        filters_json,
        next_run_at,
        last_run_at: 0,
        last_error: String::new(),
        enabled: true,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_scheduled_report(
    ctx: &ReducerContext,
    id: String,
    name: String,
    report_type: String,
    schedule_frequency: String,
    schedule_config_json: String,
    recipients_json: String,
    filters_json: String,
    next_run_at: u64,
    enabled: bool,
) {
    if let Some(r) = ctx.db.scheduled_reports().id().find(&id) {
        ctx.db.scheduled_reports().id().update(ScheduledReport {
            name,
            report_type,
            schedule_frequency,
            schedule_config_json,
            recipients_json,
            filters_json,
            next_run_at,
            enabled,
            updated_at: super::now_ms(ctx),
            ..r
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_scheduled_report(ctx: &ReducerContext, id: String) {
    ctx.db.scheduled_reports().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn mark_report_run(ctx: &ReducerContext, id: String, next_run_at: u64) {
    if let Some(r) = ctx.db.scheduled_reports().id().find(&id) {
        ctx.db.scheduled_reports().id().update(ScheduledReport {
            last_run_at: super::now_ms(ctx),
            next_run_at,
            last_error: String::new(),
            updated_at: super::now_ms(ctx),
            ..r
        });
    }
}

#[spacetimedb::reducer]
pub fn mark_report_error(ctx: &ReducerContext, id: String, error: String) {
    if let Some(r) = ctx.db.scheduled_reports().id().find(&id) {
        ctx.db.scheduled_reports().id().update(ScheduledReport {
            last_error: error,
            updated_at: super::now_ms(ctx),
            ..r
        });
    }
}

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_create_report() {
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
    fn test_update_report() {
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
    fn test_delete_report() {
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

    #[test]
    fn test_mark_run_nonexistent() {
        let ctx = test_ctx();
        // Should not panic
        mark_report_run(&ctx, "srpt_nonexistent".into(), 9999);
        assert_eq!(ctx.db.scheduled_reports().iter().count(), 0);
    }

    #[test]
    fn test_mark_error_nonexistent() {
        let ctx = test_ctx();
        // Should not panic
        mark_report_error(&ctx, "srpt_nonexistent".into(), "err".into());
        assert_eq!(ctx.db.scheduled_reports().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent() {
        let ctx = test_ctx();
        // Should not panic
        delete_scheduled_report(&ctx, "srpt_nonexistent".into());
        assert_eq!(ctx.db.scheduled_reports().iter().count(), 0);
    }
}
