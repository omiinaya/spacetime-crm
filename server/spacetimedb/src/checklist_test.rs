#[cfg(test)]
mod tests {
    use crate::checklist::ticket_checklist_items;
    use crate::ticket::ticket;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_create_checklist_template() {
        let ctx = test_ctx();
        let items = r#"[{"label":"Check power","order":1},{"label":"Test display","order":2}]"#;
        create_checklist_template(
            &ctx,
            "t_cl".into(),
            "Phone Check".into(),
            "Standard phone checklist".into(),
            items.into(),
        );
        let templates: Vec<ChecklistTemplate> = ctx.db.checklist_templates().iter().collect();
        assert_eq!(templates.len(), 1);
        let t = &templates[0];
        assert!(t.id.starts_with("clt_"));
        assert_eq!(t.name, "Phone Check");
    }

    #[test]
    fn test_update_checklist_template() {
        let ctx = test_ctx();
        create_checklist_template(&ctx, "t".into(), "Old".into(), "".into(), "[]".into());
        let id = ctx
            .db
            .checklist_templates()
            .iter()
            .next()
            .expect("expected at least one checklist_templates record")
            .id
            .clone();
        update_checklist_template(
            &ctx,
            id.clone(),
            "New".into(),
            "Updated".into(),
            r#"[{"label":"X"}]"#.into(),
        );
        let updated = ctx
            .db
            .checklist_templates()
            .id()
            .find(&id)
            .expect("expected record to exist");
        assert_eq!(updated.name, "New");
        assert_eq!(updated.description, "Updated");
    }

    #[test]
    fn test_delete_checklist_template() {
        let ctx = test_ctx();
        create_checklist_template(&ctx, "t".into(), "Del".into(), "".into(), "[]".into());
        assert_eq!(ctx.db.checklist_templates().iter().count(), 1);
        let id = ctx
            .db
            .checklist_templates()
            .iter()
            .next()
            .expect("expected at least one checklist_templates record")
            .id
            .clone();
        delete_checklist_template(&ctx, id);
        assert_eq!(ctx.db.checklist_templates().iter().count(), 0);
    }

    #[test]
    fn test_apply_checklist_template() {
        let ctx = test_ctx();
        // Need a ticket first (for tenant_id derivation)
        crate::create_ticket(
            &ctx,
            "t_ck".into(),
            "c1".into(),
            "Check ticket".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        let tkt = ctx
            .db
            .ticket()
            .iter()
            .next()
            .expect("expected at least one ticket record");
        let tid = tkt.id.clone();
        // Create template with items
        let items = r#"[{"label":"Check battery","order":1},{"label":"Test audio","order":2}]"#;
        create_checklist_template(
            &ctx,
            "t_ck".into(),
            "Audio Check".into(),
            "".into(),
            items.into(),
        );
        let tmpl = ctx
            .db
            .checklist_templates()
            .iter()
            .next()
            .expect("expected at least one checklist_templates record");
        let tmpl_id = tmpl.id.clone();

        apply_checklist_template(&ctx, tid.clone(), tmpl_id.clone());
        let checklist: Vec<TicketChecklistItem> = ctx.db.ticket_checklist_items().iter().collect();
        assert_eq!(checklist.len(), 2);
        assert!(!checklist[0].completed);
        assert_eq!(checklist[0].ticket_id, tid);
        assert_eq!(checklist[1].template_name, "Audio Check");
    }

    #[test]
    fn test_update_checklist_item() {
        let ctx = test_ctx();
        crate::create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "T".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        let tid = ctx
            .db
            .ticket()
            .iter()
            .next()
            .expect("expected at least one ticket record")
            .id
            .clone();
        create_checklist_template(
            &ctx,
            "t".into(),
            "T".into(),
            "".into(),
            r#"[{"label":"X"}]"#.into(),
        );
        let tmpl_id = ctx
            .db
            .checklist_templates()
            .iter()
            .next()
            .expect("expected at least one checklist_templates record")
            .id
            .clone();
        apply_checklist_template(&ctx, tid, tmpl_id);
        let item = ctx
            .db
            .ticket_checklist_items()
            .iter()
            .next()
            .expect("expected at least one ticket_checklist_items record");
        let item_id = item.id.clone();
        assert!(!item.completed);
        assert!(item.completed_by.is_empty());
        update_checklist_item(&ctx, item_id.clone(), true);
        let updated = ctx
            .db
            .ticket_checklist_items()
            .id()
            .find(&item_id)
            .expect("expected record to exist");
        assert!(updated.completed);
        assert!(!updated.completed_by.is_empty());
        assert!(updated.completed_at > 0);
    }

    #[test]
    fn test_delete_ticket_checklist() {
        let ctx = test_ctx();
        crate::create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "T".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        let tid = ctx
            .db
            .ticket()
            .iter()
            .next()
            .expect("expected at least one ticket record")
            .id
            .clone();
        create_checklist_template(
            &ctx,
            "t".into(),
            "T".into(),
            "".into(),
            r#"[{"label":"X"},{"label":"Y"}]"#.into(),
        );
        let tmpl_id = ctx
            .db
            .checklist_templates()
            .iter()
            .next()
            .expect("expected at least one checklist_templates record")
            .id
            .clone();
        apply_checklist_template(&ctx, tid.clone(), tmpl_id);
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 2);
        delete_ticket_checklist(&ctx, tid);
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 0);
    }
}
