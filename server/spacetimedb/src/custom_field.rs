// TODO (kanban): Replace 8 unwrap() call(s) with proper error handling
use spacetimedb::*;

// ─── Custom Field Definition ──

#[spacetimedb::table(accessor = custom_field_definitions, public)]
#[derive(Debug, Clone)]
pub struct CustomFieldDefinition {
    #[primary_key]
    pub id: String,
    #[index(btree)]
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
    ctx.db
        .custom_field_definitions()
        .insert(CustomFieldDefinition {
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
        ctx.db
            .custom_field_definitions()
            .id()
            .update(CustomFieldDefinition {
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
    #[index(btree)]
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
    tenant_id: String,
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
        let id = format!(
            "cfv_{}_{}",
            now,
            ctx.sender().to_hex().chars().take(8).collect::<String>()
        );
        ctx.db.custom_field_values().insert(CustomFieldValue {
            id,
            tenant_id,
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

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_custom_field_definition() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t_cf".into(),
            "cfd_1".into(),
            "customer".into(),
            "Serial Number".into(),
            "text".into(),
            String::new(),
            1,
            true,
            true,
        );
        let defs: Vec<CustomFieldDefinition> = ctx.db.custom_field_definitions().iter().collect();
        assert_eq!(defs.len(), 1);
        let d = &defs[0];
        assert_eq!(d.id, "cfd_1");
        assert_eq!(d.entity_type, "customer");
        assert_eq!(d.label, "Serial Number");
        assert_eq!(d.field_type, "text");
        assert!(d.required);
        assert!(d.active);
        assert_eq!(d.sort_order, 1);
        assert!(d.created_at > 0);
        assert_eq!(d.created_at, d.updated_at);
    }

    #[test]
    fn test_create_custom_field_with_options() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t".into(),
            "cfd_s".into(),
            "ticket".into(),
            "Status".into(),
            "select".into(),
            r#"["Open","Closed"]"#.into(),
            0,
            false,
            true,
        );
        let d = ctx
            .db
            .custom_field_definitions()
            .id()
            .find("cfd_s".to_string())
            .unwrap();
        assert_eq!(d.options, r#"["Open","Closed"]"#);
    }

    #[test]
    fn test_update_custom_field_definition() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t".into(),
            "cfd_u".into(),
            "cust".into(),
            "Old".into(),
            "text".into(),
            String::new(),
            1,
            false,
            true,
        );
        update_custom_field_definition(
            &ctx,
            "cfd_u".into(),
            "New Label".into(),
            "number".into(),
            String::new(),
            2,
            true,
            false,
        );
        let updated = ctx
            .db
            .custom_field_definitions()
            .id()
            .find("cfd_u".to_string())
            .unwrap();
        assert_eq!(updated.label, "New Label");
        assert_eq!(updated.field_type, "number");
        assert!(updated.required);
        assert!(!updated.active);
        assert_eq!(updated.sort_order, 2);
    }

    #[test]
    fn test_update_nonexistent_field_def() {
        let ctx = test_ctx();
        update_custom_field_definition(
            &ctx,
            "cfd_nope".into(),
            "X".into(),
            "text".into(),
            String::new(),
            0,
            false,
            true,
        );
        assert_eq!(ctx.db.custom_field_definitions().iter().count(), 0);
    }

    #[test]
    fn test_delete_custom_field_definition() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t".into(),
            "cfd_del".into(),
            "cust".into(),
            "D".into(),
            "text".into(),
            String::new(),
            0,
            false,
            true,
        );
        assert_eq!(ctx.db.custom_field_definitions().iter().count(), 1);
        delete_custom_field_definition(&ctx, "cfd_del".into());
        assert_eq!(ctx.db.custom_field_definitions().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_field_def() {
        let ctx = test_ctx();
        delete_custom_field_definition(&ctx, "cfd_nope".into());
        assert_eq!(ctx.db.custom_field_definitions().iter().count(), 0);
    }

    #[test]
    fn test_set_custom_field_value() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t".into(),
            "cfd_v".into(),
            "customer".into(),
            "SN".into(),
            "text".into(),
            String::new(),
            0,
            false,
            true,
        );
        let result = set_custom_field_value(
            &ctx,
            "cust_1".into(),
            "cfd_v".into(),
            "SN001".into(),
            "t_cfv".into(),
        );
        assert!(result.is_ok());
        let values: Vec<CustomFieldValue> = ctx.db.custom_field_values().iter().collect();
        assert_eq!(values.len(), 1);
        assert_eq!(values[0].value, "SN001");
        assert_eq!(values[0].entity_id, "cust_1");
        assert_eq!(values[0].field_id, "cfd_v");
        assert!(values[0].created_at > 0);
        assert_eq!(values[0].created_at, values[0].updated_at);
    }

    #[test]
    fn test_set_custom_field_value_update() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t".into(),
            "cfd_vu".into(),
            "customer".into(),
            "SN".into(),
            "text".into(),
            String::new(),
            0,
            false,
            true,
        );
        set_custom_field_value(
            &ctx,
            "cust_1".into(),
            "cfd_vu".into(),
            "SN001".into(),
            "t".into(),
        )
        .unwrap();
        assert_eq!(ctx.db.custom_field_values().iter().count(), 1);
        set_custom_field_value(
            &ctx,
            "cust_1".into(),
            "cfd_vu".into(),
            "SN002".into(),
            "t".into(),
        )
        .unwrap();
        assert_eq!(ctx.db.custom_field_values().iter().count(), 1);
        assert_eq!(
            ctx.db.custom_field_values().iter().next().unwrap().value,
            "SN002"
        );
    }

    #[test]
    fn test_delete_custom_field_value() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t".into(),
            "cfd_dv".into(),
            "cust".into(),
            "V".into(),
            "text".into(),
            String::new(),
            0,
            false,
            true,
        );
        set_custom_field_value(
            &ctx,
            "cust_1".into(),
            "cfd_dv".into(),
            "V001".into(),
            "t".into(),
        )
        .unwrap();
        assert_eq!(ctx.db.custom_field_values().iter().count(), 1);
        delete_custom_field_value(&ctx, "cust_1".into(), "cfd_dv".into());
        assert_eq!(ctx.db.custom_field_values().iter().count(), 0);
    }

    #[test]
    fn test_multiple_custom_field_values() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t".into(),
            "cfd_a".into(),
            "customer".into(),
            "A".into(),
            "text".into(),
            String::new(),
            0,
            false,
            true,
        );
        create_custom_field_definition(
            &ctx,
            "t".into(),
            "cfd_b".into(),
            "customer".into(),
            "B".into(),
            "text".into(),
            String::new(),
            0,
            false,
            true,
        );
        set_custom_field_value(
            &ctx,
            "cust_1".into(),
            "cfd_a".into(),
            "ValA".into(),
            "t".into(),
        )
        .unwrap();
        set_custom_field_value(
            &ctx,
            "cust_1".into(),
            "cfd_b".into(),
            "ValB".into(),
            "t".into(),
        )
        .unwrap();
        assert_eq!(ctx.db.custom_field_values().iter().count(), 2);
    }

    #[test]
    fn test_tenant_isolation() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t_a".into(),
            "cfd_1".into(),
            "customer".into(),
            "A".into(),
            "text".into(),
            String::new(),
            0,
            false,
            true,
        );
        create_custom_field_definition(
            &ctx,
            "t_b".into(),
            "cfd_2".into(),
            "customer".into(),
            "B".into(),
            "text".into(),
            String::new(),
            0,
            false,
            true,
        );
        let a_only: Vec<CustomFieldDefinition> = ctx
            .db
            .custom_field_definitions()
            .iter()
            .filter(|d| d.tenant_id == "t_a")
            .collect();
        assert_eq!(a_only.len(), 1);
        assert_eq!(a_only[0].label, "A");
    }
}
