// TODO (kanban): Replace 8 unwrap() call(s) with proper error handling
use crate::ticket::ticket;
use spacetimedb::*;

#[spacetimedb::table(accessor = checklist_templates, public)]
#[derive(Debug, Clone)]
pub struct ChecklistTemplate {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub name: String,
    pub description: String,
    /// JSON array: [{"label":"Check power","order":1}]
    pub items: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::table(accessor = ticket_checklist_items, public)]
#[derive(Debug, Clone)]
pub struct TicketChecklistItem {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub ticket_id: String,
    pub template_id: String,
    pub template_name: String,
    pub label: String,
    pub sort_order: u32,
    pub completed: bool,
    pub completed_by: String,
    pub completed_at: u64,
    pub created_at: u64,
}

#[spacetimedb::reducer]
pub fn create_checklist_template(
    ctx: &ReducerContext,
    tenant_id: String,
    name: String,
    description: String,
    items: String,
) {
    let id = super::make_id("clt", ctx);
    let now = super::now_ms(ctx);
    ctx.db.checklist_templates().insert(ChecklistTemplate {
        id,
        tenant_id,
        name,
        description,
        items,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_checklist_template(
    ctx: &ReducerContext,
    id: String,
    name: String,
    description: String,
    items: String,
) {
    if let Some(t) = ctx.db.checklist_templates().id().find(&id) {
        ctx.db.checklist_templates().id().update(ChecklistTemplate {
            name,
            description,
            items,
            updated_at: super::now_ms(ctx),
            ..t
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_checklist_template(ctx: &ReducerContext, id: String) {
    ctx.db.checklist_templates().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn apply_checklist_template(ctx: &ReducerContext, ticket_id: String, template_id: String) {
    let Some(tmpl) = ctx.db.checklist_templates().id().find(&template_id) else {
        return;
    };
    let now = super::now_ms(ctx);
    let items: Vec<serde_json::Value> = serde_json::from_str(&tmpl.items).unwrap_or_default();

    // Delete any existing checklist from this template for the same ticket (re-apply)
    let existing: Vec<TicketChecklistItem> = ctx
        .db
        .ticket_checklist_items()
        .iter()
        .filter(|i| i.ticket_id == ticket_id && i.template_id == template_id)
        .collect();
    for item in existing {
        ctx.db.ticket_checklist_items().id().delete(&item.id);
    }

    for (i, item) in items.iter().enumerate() {
        let label = item
            .get("label")
            .and_then(|v| v.as_str())
            .unwrap_or("Item")
            .to_string();
        let order = item
            .get("order")
            .and_then(|v| v.as_u64())
            .unwrap_or(i as u64) as u32;
        let ci_id = format!(
            "tci_{}_{}_{}",
            now,
            i,
            ctx.sender().to_hex().chars().take(6).collect::<String>()
        );
        // Derive tenant_id from the parent ticket
        let ticket_tenant_id = ctx
            .db
            .ticket()
            .id()
            .find(&ticket_id)
            .map_or(String::new(), |t| t.tenant_id.clone());
        ctx.db.ticket_checklist_items().insert(TicketChecklistItem {
            id: ci_id,
            tenant_id: ticket_tenant_id,
            ticket_id: ticket_id.clone(),
            template_id: template_id.clone(),
            template_name: tmpl.name.clone(),
            label,
            sort_order: order,
            completed: false,
            completed_by: String::new(),
            completed_at: 0,
            created_at: now,
        });
    }
}

#[spacetimedb::reducer]
pub fn update_checklist_item(ctx: &ReducerContext, id: String, completed: bool) {
    if let Some(item) = ctx.db.ticket_checklist_items().id().find(&id) {
        let (completed_by, completed_at) = if completed {
            (ctx.sender().to_hex().to_string(), super::now_ms(ctx))
        } else {
            (String::new(), 0u64)
        };
        ctx.db
            .ticket_checklist_items()
            .id()
            .update(TicketChecklistItem {
                completed,
                completed_by,
                completed_at,
                ..item
            });
    }
}

#[spacetimedb::reducer]
pub fn delete_ticket_checklist(ctx: &ReducerContext, ticket_id: String) {
    let items: Vec<TicketChecklistItem> = ctx
        .db
        .ticket_checklist_items()
        .iter()
        .filter(|i| i.ticket_id == ticket_id)
        .collect();
    for item in items {
        ctx.db.ticket_checklist_items().id().delete(&item.id);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ticket::ticket;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    fn setup_ticket(ctx: &ReducerContext) -> String {
        crate::create_ticket(
            ctx,
            "t_cl".into(),
            "c1".into(),
            "Checklist ticket".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            "low".into(),
        );
        ctx.db.ticket().iter().next().unwrap().id.clone()
    }

    fn setup_template(ctx: &ReducerContext) -> String {
        let items = r#"[{"label":"Check power","order":1},{"label":"Test display","order":2}]"#;
        create_checklist_template(
            ctx,
            "t_cl".into(),
            "Phone Check".into(),
            "Standard".into(),
            items.into(),
        );
        ctx.db
            .checklist_templates()
            .iter()
            .next()
            .unwrap()
            .id
            .clone()
    }

    #[test]
    fn test_create_checklist_template() {
        let ctx = test_ctx();
        let items = r#"[{"label":"Check power","order":1}]"#;
        create_checklist_template(
            &ctx,
            "t_cl".into(),
            "Basic Check".into(),
            "Desc".into(),
            items.into(),
        );
        let templates: Vec<ChecklistTemplate> = ctx.db.checklist_templates().iter().collect();
        assert_eq!(templates.len(), 1);
        let t = &templates[0];
        assert!(t.id.starts_with("clt_"));
        assert_eq!(t.name, "Basic Check");
        assert_eq!(t.description, "Desc");
        assert_eq!(t.items, items);
        assert!(t.created_at > 0);
        assert_eq!(t.created_at, t.updated_at);
    }

    #[test]
    fn test_create_empty_items_template() {
        let ctx = test_ctx();
        create_checklist_template(&ctx, "t".into(), "Empty".into(), String::new(), "[]".into());
        assert_eq!(ctx.db.checklist_templates().iter().count(), 1);
    }

    #[test]
    fn test_update_checklist_template() {
        let ctx = test_ctx();
        create_checklist_template(&ctx, "t".into(), "Old".into(), String::new(), "[]".into());
        let id = ctx
            .db
            .checklist_templates()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        update_checklist_template(
            &ctx,
            id.clone(),
            "New".into(),
            "Updated".into(),
            r#"[{"label":"X"}]"#.into(),
        );
        let updated = ctx.db.checklist_templates().id().find(&id).unwrap();
        assert_eq!(updated.name, "New");
        assert_eq!(updated.description, "Updated");
    }

    #[test]
    fn test_delete_checklist_template() {
        let ctx = test_ctx();
        create_checklist_template(&ctx, "t".into(), "Del".into(), String::new(), "[]".into());
        assert_eq!(ctx.db.checklist_templates().iter().count(), 1);
        let id = ctx
            .db
            .checklist_templates()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        delete_checklist_template(&ctx, id);
        assert_eq!(ctx.db.checklist_templates().iter().count(), 0);
    }

    #[test]
    fn test_apply_checklist_template() {
        let ctx = test_ctx();
        let tid = setup_ticket(&ctx);
        let tmpl_id = setup_template(&ctx);

        apply_checklist_template(&ctx, tid.clone(), tmpl_id);
        let checklist: Vec<TicketChecklistItem> = ctx.db.ticket_checklist_items().iter().collect();
        assert_eq!(checklist.len(), 2);
        assert!(!checklist[0].completed);
        assert_eq!(checklist[0].ticket_id, tid);
        assert_eq!(checklist[1].template_name, "Phone Check");
    }

    #[test]
    fn test_apply_checklist_reapply_clears_old() {
        let ctx = test_ctx();
        let tid = setup_ticket(&ctx);
        let tmpl_id = setup_template(&ctx);

        apply_checklist_template(&ctx, tid.clone(), tmpl_id.clone());
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 2);
        apply_checklist_template(&ctx, tid, tmpl_id);
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 2); // re-applied, not duplicated
    }

    #[test]
    fn test_update_checklist_item() {
        let ctx = test_ctx();
        let tid = setup_ticket(&ctx);
        let tmpl_id = setup_template(&ctx);
        apply_checklist_template(&ctx, tid, tmpl_id);

        let item = ctx.db.ticket_checklist_items().iter().next().unwrap();
        let item_id = item.id.clone();
        assert!(!item.completed);
        assert!(item.completed_by.is_empty());
        update_checklist_item(&ctx, item_id.clone(), true);
        let updated = ctx.db.ticket_checklist_items().id().find(&item_id).unwrap();
        assert!(updated.completed);
        assert!(!updated.completed_by.is_empty());
        assert!(updated.completed_at > 0);

        // Uncheck
        update_checklist_item(&ctx, item_id, false);
        let unchecked = ctx.db.ticket_checklist_items().iter().next().unwrap();
        assert!(!unchecked.completed);
        assert!(unchecked.completed_by.is_empty());
        assert_eq!(unchecked.completed_at, 0);
    }

    #[test]
    fn test_update_nonexistent_checklist_item() {
        let ctx = test_ctx();
        update_checklist_item(&ctx, "tci_nope".into(), true);
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 0);
    }

    #[test]
    fn test_delete_ticket_checklist() {
        let ctx = test_ctx();
        let tid = setup_ticket(&ctx);
        let tmpl_id = setup_template(&ctx);
        apply_checklist_template(&ctx, tid.clone(), tmpl_id);
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 2);
        delete_ticket_checklist(&ctx, tid);
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 0);
    }

    #[test]
    fn test_apply_checklist_no_template() {
        let ctx = test_ctx();
        let tid = setup_ticket(&ctx);
        apply_checklist_template(&ctx, tid, "clt_nope".into());
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 0);
    }

    #[test]
    fn test_apply_checklist_no_ticket() {
        let ctx = test_ctx();
        let tmpl_id = setup_template(&ctx);
        apply_checklist_template(&ctx, "tkt_nope".into(), tmpl_id);
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 0);
    }
}
