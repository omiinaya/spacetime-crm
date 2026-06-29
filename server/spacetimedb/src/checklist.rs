use spacetimedb::*;
use crate::ticket::ticket;

#[spacetimedb::table(accessor = checklist_templates, public)]
#[derive(Debug, Clone)]
pub struct ChecklistTemplate {
    #[primary_key]
    pub id: String,
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
pub fn create_checklist_template(ctx: &ReducerContext, tenant_id: String, name: String, description: String, items: String) {
    let id = super::make_id("clt", ctx);
    let now = super::now_ms(ctx);
    ctx.db.checklist_templates().insert(ChecklistTemplate {
        id, tenant_id, name, description, items,
        created_at: now, updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_checklist_template(ctx: &ReducerContext, id: String, name: String, description: String, items: String) {
    if let Some(t) = ctx.db.checklist_templates().id().find(&id) {
        ctx.db.checklist_templates().id().update(ChecklistTemplate {
            name, description, items,
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
    let Some(tmpl) = ctx.db.checklist_templates().id().find(&template_id) else { return };
    let now = super::now_ms(ctx);
    let items: Vec<serde_json::Value> = serde_json::from_str(&tmpl.items).unwrap_or_default();

    // Delete any existing checklist from this template for the same ticket (re-apply)
    let existing: Vec<TicketChecklistItem> = ctx.db.ticket_checklist_items().iter()
        .filter(|i| i.ticket_id == ticket_id && i.template_id == template_id)
        .collect();
    for item in existing {
        ctx.db.ticket_checklist_items().id().delete(&item.id);
    }

    for (i, item) in items.iter().enumerate() {
        let label = item.get("label").and_then(|v| v.as_str()).unwrap_or("Item").to_string();
        let order = item.get("order").and_then(|v| v.as_u64()).unwrap_or(i as u64) as u32;
        let ci_id = format!("tci_{}_{}_{}", now, i, ctx.sender().to_hex().chars().take(6).collect::<String>());
    // Derive tenant_id from the parent ticket
    let ticket_tenant_id = ctx.db.ticket().id().find(&ticket_id).map_or(String::new(), |t| t.tenant_id.clone());
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
        ctx.db.ticket_checklist_items().id().update(TicketChecklistItem {
            completed,
            completed_by,
            completed_at,
            ..item
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_ticket_checklist(ctx: &ReducerContext, ticket_id: String) {
    let items: Vec<TicketChecklistItem> = ctx.db.ticket_checklist_items().iter()
        .filter(|i| i.ticket_id == ticket_id)
        .collect();
    for item in items {
        ctx.db.ticket_checklist_items().id().delete(&item.id);
    }
}
