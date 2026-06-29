use spacetimedb::*;

// ─── Custom Field Definition ──

#[spacetimedb::table(accessor = custom_field_definitions, public)]
#[derive(Debug, Clone)]
pub struct CustomFieldDefinition {
    #[primary_key]
    pub id: String,
    pub tenant_id: String,
    /// Which entity this field applies to: "customer", "ticket", "invoice", "product"
    pub entity_type: String,
    /// Human-readable label shown on the form
    pub label: String,
    /// Field type: "text", "number", "date", "select", "multiselect", "checkbox", "textarea"
    pub field_type: String,
    /// JSON array of options for select/multiselect: '["Option A","Option B"]'
    pub options: String,
    /// Display order (lower = first)
    pub sort_order: u32,
    /// Whether this field is required
    pub required: bool,
    /// Whether this field is active (can be hidden without deleting)
    pub active: bool,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn create_custom_field_definition(
    ctx: &ReducerContext,
    tenant_id: String,
    id: String,
    entity_type: String,
    label: String,
    field_type: String,
    options: String,
    sort_order: u32,
    required: bool,
    active: bool,
) {
    let now = now_ms(ctx);
    ctx.db.custom_field_definitions().insert(CustomFieldDefinition {
        id,
        tenant_id,
        entity_type,
        label,
        field_type,
        options,
        sort_order,
        required,
        active,
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_custom_field_definition(
    ctx: &ReducerContext,
    id: String,
    label: String,
    field_type: String,
    options: String,
    sort_order: u32,
    required: bool,
    active: bool,
) {
    if let Some(f) = ctx.db.custom_field_definitions().id().find(&id) {
        ctx.db.custom_field_definitions().id().update(CustomFieldDefinition {
            label,
            field_type,
            options,
            sort_order,
            required,
            active,
            updated_at: now_ms(ctx),
            ..f
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_custom_field_definition(ctx: &ReducerContext, id: String) {
    ctx.db.custom_field_definitions().id().delete(&id);
}

// ─── Custom Field Value ──

#[spacetimedb::table(accessor = custom_field_values, public)]
#[derive(Debug, Clone)]
pub struct CustomFieldValue {
    #[primary_key]
    pub id: String,
    pub tenant_id: String,
    /// The entity this value belongs to (e.g. customer_<id>)
    pub entity_id: String,
    /// Which field definition this value is for
    pub field_id: String,
    /// The stored value (text for text/select/textarea, serialised for others)
    pub value: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn set_custom_field_value(
    ctx: &ReducerContext,
    entity_id: String,
    field_id: String,
    value: String,
) -> Result<(), String> {
    let now = now_ms(ctx);
    // Check if a value already exists for this entity+field combo
    let existing = ctx
        .db
        .custom_field_values()
        .iter()
        .find(|v| v.entity_id == entity_id && v.field_id == field_id);

    if let Some(existing_val) = existing {
        ctx.db.custom_field_values().id().update(CustomFieldValue {
            value,
            updated_at: now,
            ..existing_val
        });
    } else {
        let id = format!("cfv_{}_{}", now, ctx.sender().to_hex().chars().take(8).collect::<String>());
        ctx.db.custom_field_values().insert(CustomFieldValue {
            id,
            tenant_id: String::new(), // Tenant assigned at insert time by the caller
            entity_id,
            field_id,
            value,
            created_at: now,
            updated_at: now,
        });
    }
    Ok(())
}

#[spacetimedb::reducer]
pub fn delete_custom_field_value(ctx: &ReducerContext, entity_id: String, field_id: String) {
    let ids: Vec<String> = ctx
        .db
        .custom_field_values()
        .iter()
        .filter(|v| v.entity_id == entity_id && v.field_id == field_id)
        .map(|v| v.id.clone())
        .collect();
    for vid in ids {
        ctx.db.custom_field_values().id().delete(&vid);
    }
}

fn now_ms(ctx: &ReducerContext) -> u64 {
    ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000
}
