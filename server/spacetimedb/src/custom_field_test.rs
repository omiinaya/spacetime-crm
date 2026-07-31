#[cfg(test)]
mod tests {
    use crate::custom_field::custom_field_values;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
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
            "".into(),
            1,
            true,
            true,
        );
        let defs: Vec<CustomFieldDefinition> = ctx.db.custom_field_definitions().iter().collect();
        assert_eq!(defs.len(), 1);
        let d = &defs[0];
        assert_eq!(d.id, "cfd_1");
        assert_eq!(d.label, "Serial Number");
        assert_eq!(d.field_type, "text");
        assert!(d.required);
        assert!(d.active);
    }

    #[test]
    fn test_update_custom_field_definition() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t".into(),
            "cfd_1".into(),
            "cust".into(),
            "Old".into(),
            "text".into(),
            "".into(),
            1,
            false,
            true,
        );
        update_custom_field_definition(
            &ctx,
            "cfd_1".into(),
            "New Label".into(),
            "number".into(),
            "".into(),
            2,
            true,
            true,
        );
        let updated = ctx
            .db
            .custom_field_definitions()
            .id()
            .find("cfd_1".to_string())
            .expect("expected record to exist");
        assert_eq!(updated.label, "New Label");
        assert_eq!(updated.field_type, "number");
        assert!(updated.required);
        assert_eq!(updated.sort_order, 2);
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
            "".into(),
            0,
            false,
            true,
        );
        assert_eq!(ctx.db.custom_field_definitions().iter().count(), 1);
        delete_custom_field_definition(&ctx, "cfd_del".into());
        assert_eq!(ctx.db.custom_field_definitions().iter().count(), 0);
    }

    #[test]
    fn test_set_custom_field_value() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx,
            "t".into(),
            "cfd_ser".into(),
            "customer".into(),
            "SN".into(),
            "text".into(),
            "".into(),
            0,
            false,
            true,
        );
        let result1 = set_custom_field_value(
            &ctx,
            "cust_1".into(),
            "cfd_ser".into(),
            "SN001".into(),
            "t_cfv".into(),
        );
        assert!(result1.is_ok());
        let values: Vec<CustomFieldValue> = ctx.db.custom_field_values().iter().collect();
        assert_eq!(values.len(), 1);
        assert_eq!(values[0].value, "SN001");
        assert_eq!(values[0].entity_id, "cust_1");

        // Update existing value
        let result2 = set_custom_field_value(
            &ctx,
            "cust_1".into(),
            "cfd_ser".into(),
            "SN002".into(),
            "t_cfv".into(),
        );
        assert!(result2.is_ok());
        assert_eq!(ctx.db.custom_field_values().iter().count(), 1);
        assert_eq!(
            ctx.db
                .custom_field_values()
                .iter()
                .next()
                .expect("expected at least one custom_field_values record")
                .value,
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
            "".into(),
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
        .expect("expected value");
        assert_eq!(ctx.db.custom_field_values().iter().count(), 1);
        delete_custom_field_value(&ctx, "cust_1".into(), "cfd_dv".into());
        assert_eq!(ctx.db.custom_field_values().iter().count(), 0);
    }
}
