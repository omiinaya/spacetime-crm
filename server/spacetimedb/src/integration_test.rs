//! Comprehensive #[cfg(test)] integration tests for all STDB reducers.
//!
//! Uses ReducerContext::__dummy() (STDB's in-memory test context) to exercise
//! every reducer with create → read → update → delete lifecycle checks,
//! edge cases, and tenant isolation.
//!
//! Follows the existing patterns in customer_test.rs and lib_test.rs.

#[cfg(test)]
mod tests {
    use crate::*;
    // STDB accessor traits for table methods
    use crate::appointment::appointment;
    use crate::customer::customer;
    use crate::product::products;
    use crate::purchase_order::purchase_order;
    use crate::purchase_order::purchase_order_line_item;
    use crate::ticket::ticket;
    use crate::user::user;
    use crate::user::user_settings;

    // ── Helpers ──────────────────────────────────────────────────────────

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    // ──────────────────────────────────────────────────────────────────────
    //  APPOINTMENT
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_appointment() {
        let ctx = test_ctx();
        create_appointment(
            &ctx, "t_appt".into(), "cust_1".into(), "tkt_1".into(),
            "Screen repair".into(), "Replace cracked screen".into(),
            1700000000000, 1700003600000, false,
            String::new(), String::new(),
        );
        use crate::appointment::appointment;
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
        create_appointment(&ctx, "t".into(), "c1".into(), "".into(), "Test".into(), "".into(), 1000, 2000, false, "".into(), "".into(), "".into());
        let a = ctx.db.appointment().iter().next().unwrap();
        assert_eq!(a.status, "scheduled");
        let id = a.id.clone();
        update_appointment_status(&ctx, id.clone(), "completed".into());
        let updated = ctx.db.appointment().id().find(&id).unwrap();
        assert_eq!(updated.status, "completed");
    }

    #[test]
    fn test_set_recurrence() {
        let ctx = test_ctx();
        create_appointment(&ctx, "t".into(), "c1".into(), "".into(), "Recur".into(), "".into(), 1000, 2000, false, "".into(), "".into(), "".into());
        let a = ctx.db.appointment().iter().next().unwrap();
        let id = a.id.clone();
        assert!(a.recurrence_rule.is_empty());
        let rule = "FREQ=WEEKLY;BYDAY=MO";
        set_recurrence(&ctx, id.clone(), rule.into());
        let updated = ctx.db.appointment().id().find(&id).unwrap();
        assert_eq!(updated.recurrence_rule, rule);
    }

    #[test]
    fn test_generate_next_occurrence() {
        let ctx = test_ctx();
        create_appointment(&ctx, "t".into(), "c1".into(), "".into(), "Series".into(), "".into(), 1000, 2000, false, "".into(), "FREQ=WEEKLY".into(), "".into());
        let parent = ctx.db.appointment().iter().next().unwrap();
        let series_id = parent.id.clone();
        assert_eq!(ctx.db.appointment().iter().count(), 1);
        generate_next_occurrence(&ctx, series_id.clone(), 2000, 3000, "FREQ=WEEKLY".into());
        assert_eq!(ctx.db.appointment().iter().count(), 2);
    }

    #[test]
    fn test_delete_appointment() {
        let ctx = test_ctx();
        create_appointment(&ctx, "t".into(), "c1".into(), "".into(), "Del".into(), "".into(), 1000, 2000, false, "".into(), "".into(), "".into());
        assert_eq!(ctx.db.appointment().iter().count(), 1);
        let id = ctx.db.appointment().iter().next().unwrap().id.clone();
        delete_appointment(&ctx, id);
        assert_eq!(ctx.db.appointment().iter().count(), 0);
    }

    #[test]
    fn test_update_nonexistent_appointment_doesnt_panic() {
        let ctx = test_ctx();
        update_appointment_status(&ctx, "appt_nonexistent".into(), "completed".into());
        assert_eq!(ctx.db.appointment().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  AUDIT
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_log_audit() {
        let ctx = test_ctx();
        log_audit(&ctx, "t_aud".into(), "user_1".into(), "Alice".into(),
            "created".into(), "customer".into(), "cust_1".into(),
            r#"{"name":"Alice"}"#.into());
        let logs: Vec<AuditLog> = ctx.db.audit_log().iter().collect();
        assert_eq!(logs.len(), 1);
        let l = &logs[0];
        assert!(l.id.starts_with("aud_"));
        assert_eq!(l.action, "created");
        assert_eq!(l.entity, "customer");
        assert_eq!(l.user_name, "Alice");
    }

    // ──────────────────────────────────────────────────────────────────────
    //  CHECKLIST
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_checklist_template() {
        let ctx = test_ctx();
        let items = r#"[{"label":"Check power","order":1},{"label":"Test display","order":2}]"#;
        create_checklist_template(&ctx, "t_cl".into(), "Phone Check".into(), "Standard phone checklist".into(), items.into());
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
        let id = ctx.db.checklist_templates().iter().next().unwrap().id.clone();
        update_checklist_template(&ctx, id.clone(), "New".into(), "Updated".into(), r#"[{"label":"X"}]"#.into());
        let updated = ctx.db.checklist_templates().id().find(&id).unwrap();
        assert_eq!(updated.name, "New");
        assert_eq!(updated.description, "Updated");
    }

    #[test]
    fn test_delete_checklist_template() {
        let ctx = test_ctx();
        create_checklist_template(&ctx, "t".into(), "Del".into(), "".into(), "[]".into());
        assert_eq!(ctx.db.checklist_templates().iter().count(), 1);
        let id = ctx.db.checklist_templates().iter().next().unwrap().id.clone();
        delete_checklist_template(&ctx, id);
        assert_eq!(ctx.db.checklist_templates().iter().count(), 0);
    }

    #[test]
    fn test_apply_checklist_template() {
        let ctx = test_ctx();
        // Need a ticket first (for tenant_id derivation)
        crate::create_ticket(&ctx, "t_ck".into(), "c1".into(), "Check ticket".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        let tkt = ctx.db.ticket().iter().next().unwrap();
        let tid = tkt.id.clone();
        // Create template with items
        let items = r#"[{"label":"Check battery","order":1},{"label":"Test audio","order":2}]"#;
        create_checklist_template(&ctx, "t_ck".into(), "Audio Check".into(), "".into(), items.into());
        let tmpl = ctx.db.checklist_templates().iter().next().unwrap();
        let tmpl_id = tmpl.id.clone();

        apply_checklist_template(&ctx, tid.clone(), tmpl_id.clone());
        use crate::checklist::ticket_checklist_items;
        let checklist: Vec<TicketChecklistItem> = ctx.db.ticket_checklist_items().iter().collect();
        assert_eq!(checklist.len(), 2);
        assert!(!checklist[0].completed);
        assert_eq!(checklist[0].ticket_id, tid);
        assert_eq!(checklist[1].template_name, "Audio Check");
    }

    #[test]
    fn test_update_checklist_item() {
        let ctx = test_ctx();
        crate::create_ticket(&ctx, "t".into(), "c1".into(), "T".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        let tid = ctx.db.ticket().iter().next().unwrap().id.clone();
        create_checklist_template(&ctx, "t".into(), "T".into(), "".into(), r#"[{"label":"X"}]"#.into());
        let tmpl_id = ctx.db.checklist_templates().iter().next().unwrap().id.clone();
        apply_checklist_template(&ctx, tid, tmpl_id);
        use crate::checklist::ticket_checklist_items;
        let item = ctx.db.ticket_checklist_items().iter().next().unwrap();
        let item_id = item.id.clone();
        assert!(!item.completed);
        assert!(item.completed_by.is_empty());
        update_checklist_item(&ctx, item_id.clone(), true);
        let updated = ctx.db.ticket_checklist_items().id().find(&item_id).unwrap();
        assert!(updated.completed);
        assert!(!updated.completed_by.is_empty());
        assert!(updated.completed_at > 0);
    }

    #[test]
    fn test_delete_ticket_checklist() {
        let ctx = test_ctx();
        crate::create_ticket(&ctx, "t".into(), "c1".into(), "T".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        let tid = ctx.db.ticket().iter().next().unwrap().id.clone();
        create_checklist_template(&ctx, "t".into(), "T".into(), "".into(), r#"[{"label":"X"},{"label":"Y"}]"#.into());
        let tmpl_id = ctx.db.checklist_templates().iter().next().unwrap().id.clone();
        apply_checklist_template(&ctx, tid.clone(), tmpl_id);
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 2);
        delete_ticket_checklist(&ctx, tid);
        assert_eq!(ctx.db.ticket_checklist_items().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  CUSTOM FIELD
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_custom_field_definition() {
        let ctx = test_ctx();
        create_custom_field_definition(
            &ctx, "t_cf".into(), "cfd_1".into(), "customer".into(),
            "Serial Number".into(), "text".into(), "".into(), 1, true, true,
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
        create_custom_field_definition(&ctx, "t".into(), "cfd_1".into(), "cust".into(), "Old".into(), "text".into(), "".into(), 1, false, true);
        update_custom_field_definition(&ctx, "cfd_1".into(), "New Label".into(), "number".into(), "".into(), 2, true, true);
        let updated = ctx.db.custom_field_definitions().id().find("cfd_1".to_string()).unwrap();
        assert_eq!(updated.label, "New Label");
        assert_eq!(updated.field_type, "number");
        assert!(updated.required);
        assert_eq!(updated.sort_order, 2);
    }

    #[test]
    fn test_delete_custom_field_definition() {
        let ctx = test_ctx();
        create_custom_field_definition(&ctx, "t".into(), "cfd_del".into(), "cust".into(), "D".into(), "text".into(), "".into(), 0, false, true);
        assert_eq!(ctx.db.custom_field_definitions().iter().count(), 1);
        delete_custom_field_definition(&ctx, "cfd_del".into());
        assert_eq!(ctx.db.custom_field_definitions().iter().count(), 0);
    }

    #[test]
    fn test_set_custom_field_value() {
        let ctx = test_ctx();
        create_custom_field_definition(&ctx, "t".into(), "cfd_ser".into(), "customer".into(), "SN".into(), "text".into(), "".into(), 0, false, true);
        let result1 = set_custom_field_value(&ctx, "cust_1".into(), "cfd_ser".into(), "SN001".into(), "t_cfv".into());
        assert!(result1.is_ok());
        use crate::custom_field::custom_field_values;
        let values: Vec<CustomFieldValue> = ctx.db.custom_field_values().iter().collect();
        assert_eq!(values.len(), 1);
        assert_eq!(values[0].value, "SN001");
        assert_eq!(values[0].entity_id, "cust_1");

        // Update existing value
        let result2 = set_custom_field_value(&ctx, "cust_1".into(), "cfd_ser".into(), "SN002".into(), "t_cfv".into());
        assert!(result2.is_ok());
        assert_eq!(ctx.db.custom_field_values().iter().count(), 1);
        assert_eq!(ctx.db.custom_field_values().iter().next().unwrap().value, "SN002");
    }

    #[test]
    fn test_delete_custom_field_value() {
        let ctx = test_ctx();
        create_custom_field_definition(&ctx, "t".into(), "cfd_dv".into(), "cust".into(), "V".into(), "text".into(), "".into(), 0, false, true);
        set_custom_field_value(&ctx, "cust_1".into(), "cfd_dv".into(), "V001".into(), "t".into()).unwrap();
        assert_eq!(ctx.db.custom_field_values().iter().count(), 1);
        delete_custom_field_value(&ctx, "cust_1".into(), "cfd_dv".into());
        assert_eq!(ctx.db.custom_field_values().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  CUSTOMER GEOLOCATION
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_set_customer_geolocation() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t_geo".into(), "cust_1".into(), 40.7128, -74.0060);
        let geos: Vec<CustomerGeolocation> = ctx.db.customer_geolocations().iter().collect();
        assert_eq!(geos.len(), 1);
        let g = &geos[0];
        assert_eq!(g.customer_id, "cust_1");
        assert!((g.latitude - 40.7128).abs() < 0.001);
        assert!((g.longitude - -74.0060).abs() < 0.001);
    }

    #[test]
    fn test_set_customer_geolocation_upsert() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t".into(), "cust_1".into(), 40.0, -74.0);
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 1);
        set_customer_geolocation(&ctx, "t".into(), "cust_1".into(), 41.0, -73.0);
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 1);
        assert!((ctx.db.customer_geolocations().iter().next().unwrap().latitude - 41.0).abs() < 0.001);
    }

    #[test]
    fn test_delete_customer_geolocation() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t".into(), "cust_1".into(), 10.0, 20.0);
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 1);
        delete_customer_geolocation(&ctx, "cust_1".into());
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  INVENTORY ADJUSTMENT
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_inventory_adjustment() {
        let ctx = test_ctx();
        // Create a product first
        create_product(&ctx, "t_inv".into(), "Battery".into(), "BAT-001".into(), "".into(), "".into(), "Parts".into(), 19.99, 8.00, 100.0, 10.0, "A-1".into());
        let prod = ctx.db.products().iter().next().unwrap();
        let pid = prod.id.clone();
        assert_eq!(prod.quantity_on_hand, 100.0);

        create_inventory_adjustment(&ctx, "t_inv".into(), pid.clone(), -5.0, "sold".into(), "".into(), "Sold 5 units".into(), "user_1".into());
        let adjustments: Vec<InventoryAdjustment> = ctx.db.inventory_adjustment().iter().collect();
        assert_eq!(adjustments.len(), 1);
        let adj = &adjustments[0];
        assert!(adj.id.starts_with("adj_"));
        assert_eq!(adj.quantity_change, -5.0);
        assert_eq!(adj.reason, "sold");

        // Verify product quantity was updated
        use crate::product::products;
        let updated = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated.quantity_on_hand, 95.0);
        assert_eq!(updated.quantity_available, 95.0);
    }

    #[test]
    fn test_inventory_adjustment_clamps_to_zero() {
        let ctx = test_ctx();
        create_product(&ctx, "t".into(), "Item".into(), "ITM".into(), "".into(), "".into(), "".into(), 5.0, 2.0, 3.0, 0.0, "".into());
        let pid = ctx.db.products().iter().next().unwrap().id.clone();
        create_inventory_adjustment(&ctx, "t".into(), pid.clone(), -10.0, "damaged".into(), "".into(), "".into(), "u".into());
        let updated = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated.quantity_on_hand, 0.0); // clamped to 0
    }

    #[test]
    fn test_delete_inventory_adjustment() {
        let ctx = test_ctx();
        create_product(&ctx, "t".into(), "P".into(), "P".into(), "".into(), "".into(), "".into(), 1.0, 0.5, 10.0, 0.0, "".into());
        let pid = ctx.db.products().iter().next().unwrap().id.clone();
        create_inventory_adjustment(&ctx, "t".into(), pid, 5.0, "received".into(), "".into(), "".into(), "u".into());
        assert_eq!(ctx.db.inventory_adjustment().iter().count(), 1);
        let id = ctx.db.inventory_adjustment().iter().next().unwrap().id.clone();
        delete_inventory_adjustment(&ctx, id);
        assert_eq!(ctx.db.inventory_adjustment().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  POS / COUNTER SALE
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_counter_sale() {
        let ctx = test_ctx();
        create_counter_sale(&ctx, "t_pos".into(), "cust_1".into(), "Walk-in".into(), "cash".into(), 100.0, 8.0, 0.0, "USD".into());
        use crate::pos::counter_sale;
        let sales: Vec<CounterSale> = ctx.db.counter_sale().iter().collect();
        assert_eq!(sales.len(), 1);
        let s = &sales[0];
        assert!(s.id.starts_with("pos_"));
        assert_eq!(s.status, "completed");
        assert_eq!(s.receipt_number, 1001);
    }

    #[test]
    fn test_add_counter_sale_item() {
        let ctx = test_ctx();
        create_counter_sale(&ctx, "t".into(), "c1".into(), "John".into(), "cash".into(), 50.0, 8.0, 0.0, "USD".into());
        let sale_id = ctx.db.counter_sale().iter().next().unwrap().id.clone();
        create_product(&ctx, "t".into(), "Cable".into(), "CBL".into(), "".into(), "".into(), "Acc".into(), 9.99, 4.0, 20.0, 0.0, "".into());
        let prod_id = ctx.db.products().iter().next().unwrap().id.clone();
        add_counter_sale_item(&ctx, "t".into(), sale_id.clone(), prod_id, "Cable".into(), "CBL".into(), 2.0, 9.99);

        // Verify line item
        use crate::pos::counter_sale_line_item;
        let items: Vec<CounterSaleLineItem> = ctx.db.counter_sale_line_item().iter().collect();
        assert_eq!(items.len(), 1);
        let item = &items[0];
        assert!(item.id.starts_with("psl_"));

        // Verify sale totals were recalculated
        use crate::pos::counter_sale;
        let sale = ctx.db.counter_sale().id().find(&sale_id).unwrap();
        assert_eq!(sale.items_count, 1);
        assert!((sale.subtotal - 19.98).abs() < 0.01);
        assert!(sale.total > 0.0);
    }

    #[test]
    fn test_refund_counter_sale() {
        let ctx = test_ctx();
        create_counter_sale(&ctx, "t".into(), "c1".into(), "".into(), "card".into(), 30.0, 0.0, 0.0, "USD".into());
        let sale_id = ctx.db.counter_sale().iter().next().unwrap().id.clone();
        assert_eq!(ctx.db.counter_sale().id().find(&sale_id).unwrap().status, "completed");
        refund_counter_sale(&ctx, sale_id.clone());
        let refunded = ctx.db.counter_sale().id().find(&sale_id).unwrap();
        assert_eq!(refunded.status, "refunded");
        assert!(refunded.refunded_at > 0);
    }

    #[test]
    fn test_delete_counter_sale() {
        let ctx = test_ctx();
        create_counter_sale(&ctx, "t".into(), "c1".into(), "".into(), "cash".into(), 10.0, 0.0, 0.0, "USD".into());
        let sale_id = ctx.db.counter_sale().iter().next().unwrap().id.clone();
        // Add a line item
        create_product(&ctx, "t".into(), "P".into(), "P".into(), "".into(), "".into(), "".into(), 5.0, 2.0, 10.0, 0.0, "".into());
        let pid = ctx.db.products().iter().next().unwrap().id.clone();
        add_counter_sale_item(&ctx, "t".into(), sale_id.clone(), pid, "P".into(), "P".into(), 1.0, 5.0);

        assert_eq!(ctx.db.counter_sale().iter().count(), 1);
        assert_eq!(ctx.db.counter_sale_line_item().iter().count(), 1);
        delete_counter_sale(&ctx, sale_id);
        assert_eq!(ctx.db.counter_sale().iter().count(), 0);
        assert_eq!(ctx.db.counter_sale_line_item().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  SLA CONFIG
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_upsert_sla_config() {
        let ctx = test_ctx();
        let targets = r#"{"urgent":4,"high":24,"medium":72,"low":120}"#;
        upsert_sla_config(&ctx, "t_sla".into(), targets.into());
        let configs: Vec<SlaConfig> = ctx.db.sla_configs().iter().collect();
        assert_eq!(configs.len(), 1);
        let c = &configs[0];
        assert_eq!(c.tenant_id, "t_sla");
        assert_eq!(c.targets_json, targets);
        assert!(c.updated_at > 0);
        assert!(!c.updated_by.is_empty());
    }

    #[test]
    fn test_upsert_sla_config_update() {
        let ctx = test_ctx();
        upsert_sla_config(&ctx, "t_sla".into(), r#"{"urgent":4}"#.into());
        assert_eq!(ctx.db.sla_configs().iter().count(), 1);
        // Update same tenant
        upsert_sla_config(&ctx, "t_sla".into(), r#"{"urgent":2}"#.into());
        assert_eq!(ctx.db.sla_configs().iter().count(), 1);
        let updated = ctx.db.sla_configs().tenant_id().find(&"t_sla".into()).unwrap();
        assert_eq!(updated.targets_json, r#"{"urgent":2}"#);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  TAX RATE
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t_tax".into(), "Sales Tax".into(), 8.875, true);
        use crate::tax_rate::tax_rates;
        let rates: Vec<TaxRate> = ctx.db.tax_rates().iter().collect();
        assert_eq!(rates.len(), 1);
        let r = &rates[0];
        assert!(r.id.starts_with("tax_"));
        assert_eq!(r.name, "Sales Tax");
        assert!((r.rate - 8.875).abs() < 0.001);
        assert!(r.is_default);
    }

    #[test]
    fn test_update_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t".into(), "Old".into(), 5.0, false);
        let id = ctx.db.tax_rates().iter().next().unwrap().id.clone();
        update_tax_rate(&ctx, id.clone(), "New".into(), 6.0, true);
        let updated = ctx.db.tax_rates().id().find(&id).unwrap();
        assert_eq!(updated.name, "New");
        assert!((updated.rate - 6.0).abs() < 0.001);
        assert!(updated.is_default);
    }

    #[test]
    fn test_tax_rate_default_clears_others() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t".into(), "Rate A".into(), 5.0, true);
        let a_id = ctx.db.tax_rates().iter().next().unwrap().id.clone();
        create_tax_rate(&ctx, "t".into(), "Rate B".into(), 8.0, true);
        // A should now be non-default, B is default
        let a = ctx.db.tax_rates().id().find(&a_id).unwrap();
        assert!(!a.is_default);
        let b = ctx.db.tax_rates().iter().find(|r| r.id != a_id).unwrap();
        assert!(b.is_default);
    }

    #[test]
    fn test_delete_tax_rate() {
        let ctx = test_ctx();
        create_tax_rate(&ctx, "t".into(), "Del".into(), 3.0, false);
        assert_eq!(ctx.db.tax_rates().iter().count(), 1);
        let id = ctx.db.tax_rates().iter().next().unwrap().id.clone();
        delete_tax_rate(&ctx, id);
        assert_eq!(ctx.db.tax_rates().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  TENANT
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_tenant() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Joe's Repair".into(), "joes-repair".into());
        use crate::tenant::tenants;
        let tenants: Vec<Tenant> = ctx.db.tenants().iter().collect();
        assert_eq!(tenants.len(), 1);
        let t = &tenants[0];
        assert!(t.id.starts_with("tnt_"));
        assert_eq!(t.name, "Joe's Repair");
    }

    #[test]
    fn test_update_tenant() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Old Shop".into(), "old-shop".into());
        let id = ctx.db.tenants().iter().next().unwrap().id.clone();
        update_tenant(&ctx, id.clone(), "New Shop".into(), "new-shop".into(), "https://logo.url".into(), r#"{"theme":"dark"}"#.into());
        let updated = ctx.db.tenants().id().find(&id).unwrap();
        assert_eq!(updated.name, "New Shop");
        assert_eq!(updated.slug, "new-shop");
        assert_eq!(updated.logo_url, "https://logo.url");
        assert_eq!(updated.settings, r#"{"theme":"dark"}"#);
    }

    #[test]
    fn test_delete_tenant() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Del Shop".into(), "del-shop".into());
        let id = ctx.db.tenants().iter().next().unwrap().id.clone();
        // Add a member first
        add_tenant_member(&ctx, id.clone(), "user_1".into(), "admin".into());
        assert_eq!(ctx.db.tenants().iter().count(), 1);
        assert_eq!(ctx.db.tenant_members().iter().count(), 1);
        delete_tenant(&ctx, id);
        assert_eq!(ctx.db.tenants().iter().count(), 0);
        assert_eq!(ctx.db.tenant_members().iter().count(), 0); // cascade
    }

    #[test]
    fn test_add_remove_tenant_member() {
        let ctx = test_ctx();
        create_tenant(&ctx, "Shop".into(), "shop".into());
        let tid = ctx.db.tenants().iter().next().unwrap().id.clone();
        add_tenant_member(&ctx, tid.clone(), "tech_1".into(), "user".into());
        let members = ctx.db.tenant_members().iter().collect::<Vec<_>>();
        assert_eq!(members.len(), 1);
        assert_eq!(members[0].username, "tech_1");
        assert_eq!(members[0].role, "user");
        let mem_id = members[0].id.clone();
        remove_tenant_member(&ctx, mem_id);
        assert_eq!(ctx.db.tenant_members().iter().count(), 0);
    }

    #[test]
    fn test_update_tenant_member_role() {
        let ctx = test_ctx();
        create_tenant(&ctx, "S".into(), "s".into());
        add_tenant_member(&ctx, ctx.db.tenants().iter().next().unwrap().id.clone(), "admin_u".into(), "user".into());
        let member = ctx.db.tenant_members().iter().next().unwrap();
        let mem_id = member.id.clone();
        assert_eq!(member.role, "user");
        update_tenant_member_role(&ctx, mem_id.clone(), "admin".into());
        let updated = ctx.db.tenant_members().id().find(&mem_id).unwrap();
        assert_eq!(updated.role, "admin");
    }

    // ──────────────────────────────────────────────────────────────────────
    //  USER
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_user() {
        let ctx = test_ctx();
        create_user(&ctx, "alice".into(), "alice@test.com".into(), "tech".into());
        let users: Vec<User> = ctx.db.user().iter().collect();
        assert_eq!(users.len(), 1);
        let u = &users[0];
        assert!(u.id.starts_with("user_"));
        assert_eq!(u.name, "alice");
        assert_eq!(u.email, "alice@test.com");
        assert_eq!(u.role, "tech");
        assert!(u.active);
        assert!(u.password_hash.is_empty());
        assert!(!u.totp_enabled);
    }

    #[test]
    fn test_update_user() {
        let ctx = test_ctx();
        create_user(&ctx, "bob".into(), "bob@t.com".into(), "tech".into());
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        update_user(&ctx, id.clone(), "bob_updated".into(), "bob@new.com".into(), "admin".into(), false);
        let updated = ctx.db.user().id().find(&id).unwrap();
        assert_eq!(updated.name, "bob_updated");
        assert_eq!(updated.email, "bob@new.com");
        assert_eq!(updated.role, "admin");
        assert!(!updated.active);
    }

    #[test]
    fn test_set_user_password() {
        let ctx = test_ctx();
        create_user(&ctx, "charlie".into(), "c@t.com".into(), "front_desk".into());
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        assert!(ctx.db.user().id().find(&id).unwrap().password_hash.is_empty());
        let hash = "bcrypt_hash_abc123".to_string();
        set_user_password(&ctx, id.clone(), hash.clone());
        assert_eq!(ctx.db.user().id().find(&id).unwrap().password_hash, hash);
    }

    #[test]
    fn test_user_totp_lifecycle() {
        let ctx = test_ctx();
        create_user(&ctx, "dave".into(), "d@t.com".into(), "admin".into());
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        // Initial state
        assert!(!ctx.db.user().id().find(&id).unwrap().totp_enabled);
        assert!(ctx.db.user().id().find(&id).unwrap().totp_secret.is_empty());
        // Set secret
        let secret = "TEST_TOTP_SECRET_VALUE".to_string();
        set_user_totp_secret(&ctx, id.clone(), secret.clone());
        let u = ctx.db.user().id().find(&id).unwrap();
        assert_eq!(u.totp_secret, secret);
        assert!(!u.totp_enabled);
        // Enable
        enable_user_totp(&ctx, id.clone());
        assert!(ctx.db.user().id().find(&id).unwrap().totp_enabled);
        // Disable
        disable_user_totp(&ctx, id.clone());
        let u2 = ctx.db.user().id().find(&id).unwrap();
        assert!(!u2.totp_enabled);
        assert!(u2.totp_secret.is_empty());
    }

    #[test]
    fn test_delete_user() {
        let ctx = test_ctx();
        create_user(&ctx, "eve".into(), "e@t.com".into(), "tech".into());
        assert_eq!(ctx.db.user().iter().count(), 1);
        let id = ctx.db.user().iter().next().unwrap().id.clone();
        delete_user(&ctx, id);
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_update_nonexistent_user_doesnt_panic() {
        let ctx = test_ctx();
        update_user(&ctx, "user_nonexistent".into(), "n".into(), "n@t.com".into(), "tech".into(), true);
        assert_eq!(ctx.db.user().iter().count(), 0);
        set_user_password(&ctx, "user_nonexistent".into(), "hash".into());
        set_user_totp_secret(&ctx, "user_nonexistent".into(), "sec".into());
        enable_user_totp(&ctx, "user_nonexistent".into());
        disable_user_totp(&ctx, "user_nonexistent".into());
        delete_user(&ctx, "user_nonexistent".into());
        // No crash means success
    }

    // ──────────────────────────────────────────────────────────────────────
    //  WEBHOOK
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_webhook_subscription() {
        let ctx = test_ctx();
        create_webhook_subscription(&ctx, "t_wh".into(), "https://hooks.example.com".into(),
            "ticket.created,ticket.updated".into(), "sec_123".into());
        use crate::webhook::webhook_subscriptions;
        let subs: Vec<WebhookSubscription> = ctx.db.webhook_subscriptions().iter().collect();
        assert_eq!(subs.len(), 1);
        let s = &subs[0];
        assert!(s.id.starts_with("whk_"));
        assert_eq!(s.url, "https://hooks.example.com");
        assert!(s.active);
    }

    #[test]
    fn test_update_webhook_subscription() {
        let ctx = test_ctx();
        create_webhook_subscription(&ctx, "t".into(), "https://old.url".into(), "ticket.created".into(), "".into());
        let id = ctx.db.webhook_subscriptions().iter().next().unwrap().id.clone();
        update_webhook_subscription(&ctx, id.clone(), "https://new.url".into(),
            "customer.*".into(), "new_secret".into(), false);
        let updated = ctx.db.webhook_subscriptions().id().find(&id).unwrap();
        assert_eq!(updated.url, "https://new.url");
        assert_eq!(updated.events, "customer.*");
        assert!(!updated.active);
    }

    #[test]
    fn test_delete_webhook_subscription() {
        let ctx = test_ctx();
        create_webhook_subscription(&ctx, "t".into(), "https://del.url".into(), "a".into(), "".into());
        assert_eq!(ctx.db.webhook_subscriptions().iter().count(), 1);
        let id = ctx.db.webhook_subscriptions().iter().next().unwrap().id.clone();
        delete_webhook_subscription(&ctx, id);
        assert_eq!(ctx.db.webhook_subscriptions().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  RECURRING INVOICE RULES (lib.rs)
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_recurring_invoice_rule() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(&ctx, "t_rir".into(), "cust_1".into(),
            "Monthly Rent".into(), "monthly".into(), 1, 15,
            r#"[{"description":"Rent","quantity":1,"unit_price":1000}]"#.into(),
            "USD".into(),
            1700000000000);
        let rules: Vec<RecurringInvoiceRule> = ctx.db.recurring_invoice_rules().iter().collect();
        assert_eq!(rules.len(), 1);
        let r = &rules[0];
        assert!(r.id.starts_with("rir_"));
        assert_eq!(r.status, "active");
        assert_eq!(r.frequency, "monthly");
    }

    #[test]
    fn test_update_recurring_invoice_rule() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(&ctx, "t".into(), "c1".into(), "Old".into(), "monthly".into(), 1, 15, "[]".into(), "USD".into(), 1000);
        let id = ctx.db.recurring_invoice_rules().iter().next().unwrap().id.clone();
        update_recurring_invoice_rule(&ctx, id.clone(), "New Name".into(), "weekly".into(), 2, 30, r#"[{"desc":"X"}]"#.into(), "USD".into(), 2000, "paused".into());
        let updated = ctx.db.recurring_invoice_rules().id().find(&id).unwrap();
        assert_eq!(updated.name, "New Name");
        assert_eq!(updated.frequency, "weekly");
        assert_eq!(updated.status, "paused");
    }

    #[test]
    fn test_delete_recurring_invoice_rule() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(&ctx, "t".into(), "c1".into(), "Del".into(), "m".into(), 1, 15, "[]".into(), "USD".into(), 1000);
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 1);
        let id = ctx.db.recurring_invoice_rules().iter().next().unwrap().id.clone();
        delete_recurring_invoice_rule(&ctx, id);
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  SAVED PAYMENT METHODS (lib.rs)
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_save_payment_method() {
        let ctx = test_ctx();
        save_payment_method(&ctx, "t_pm".into(), "cust_1".into(),
            "pm_stripe_123".into(), "Visa".into(), "4242".into(), 12, 2028);
        let methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter().collect();
        assert_eq!(methods.len(), 1);
        let m = &methods[0];
        assert!(m.id.starts_with("pm_"));
        assert_eq!(m.brand, "Visa");
        assert_eq!(m.last4, "4242");
        assert!(m.is_default); // First method = default
    }

    #[test]
    fn test_set_default_payment_method() {
        let ctx = test_ctx();
        save_payment_method(&ctx, "t".into(), "cust_1".into(), "pm_s1".into(), "Visa".into(), "1111".into(), 1, 2025);
        save_payment_method(&ctx, "t".into(), "cust_1".into(), "pm_s2".into(), "MC".into(), "2222".into(), 2, 2026);
        let methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter().collect();
        assert_eq!(methods.len(), 2);
        // First method was default, now set second as default
        let second = methods.iter().find(|m| m.last4 == "2222").unwrap();
        set_default_payment_method(&ctx, second.id.clone(), "cust_1".into());
        let updated_methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter().collect();
        let first = updated_methods.iter().find(|m| m.last4 == "1111").unwrap();
        let second2 = updated_methods.iter().find(|m| m.last4 == "2222").unwrap();
        assert!(!first.is_default);
        assert!(second2.is_default);
    }

    #[test]
    fn test_delete_payment_method() {
        let ctx = test_ctx();
        save_payment_method(&ctx, "t".into(), "c1".into(), "pm_d".into(), "V".into(), "0000".into(), 1, 2025);
        assert_eq!(ctx.db.saved_payment_methods().iter().count(), 1);
        let id = ctx.db.saved_payment_methods().iter().next().unwrap().id.clone();
        delete_payment_method(&ctx, id);
        assert_eq!(ctx.db.saved_payment_methods().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  SCHEDULED REPORTS (lib.rs)
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_scheduled_report() {
        let ctx = test_ctx();
        create_scheduled_report(&ctx, "t_sr".into(), "Weekly Summary".into(), "revenue".into(),
            "weekly".into(), r#"{"day":"Mon"}"#.into(), r#"["alice@test.com"]"#.into(),
            r#"{"tenant_id":"t_sr"}"#.into(), 1700000000000);
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
        create_scheduled_report(&ctx, "t".into(), "Old".into(), "rev".into(), "d".into(), "{}".into(), "[]".into(), "{}".into(), 1000);
        let id = ctx.db.scheduled_reports().iter().next().unwrap().id.clone();
        update_scheduled_report(&ctx, id.clone(), "New Name".into(), "expenses".into(), "monthly".into(),
            r#"{"day":1}"#.into(), r#"["b@t.com"]"#.into(), r#"{"x":1}"#.into(), 2000, false);
        let updated = ctx.db.scheduled_reports().id().find(&id).unwrap();
        assert_eq!(updated.name, "New Name");
        assert_eq!(updated.report_type, "expenses");
        assert!(!updated.enabled);
    }

    #[test]
    fn test_delete_scheduled_report() {
        let ctx = test_ctx();
        create_scheduled_report(&ctx, "t".into(), "Del".into(), "r".into(), "d".into(), "{}".into(), "[]".into(), "{}".into(), 1000);
        assert_eq!(ctx.db.scheduled_reports().iter().count(), 1);
        let id = ctx.db.scheduled_reports().iter().next().unwrap().id.clone();
        delete_scheduled_report(&ctx, id);
        assert_eq!(ctx.db.scheduled_reports().iter().count(), 0);
    }

    #[test]
    fn test_mark_report_run() {
        let ctx = test_ctx();
        create_scheduled_report(&ctx, "t".into(), "R".into(), "r".into(), "d".into(), "{}".into(), "[]".into(), "{}".into(), 1000);
        let id = ctx.db.scheduled_reports().iter().next().unwrap().id.clone();
        assert_eq!(ctx.db.scheduled_reports().id().find(&id).unwrap().last_run_at, 0);
        mark_report_run(&ctx, id.clone(), 2000);
        let updated = ctx.db.scheduled_reports().id().find(&id).unwrap();
        assert!(updated.last_run_at > 0);
        assert_eq!(updated.next_run_at, 2000);
    }

    #[test]
    fn test_mark_report_error() {
        let ctx = test_ctx();
        create_scheduled_report(&ctx, "t".into(), "Err".into(), "r".into(), "d".into(), "{}".into(), "[]".into(), "{}".into(), 1000);
        let id = ctx.db.scheduled_reports().iter().next().unwrap().id.clone();
        assert!(ctx.db.scheduled_reports().id().find(&id).unwrap().last_error.is_empty());
        mark_report_error(&ctx, id.clone(), "API timeout".into());
        assert_eq!(ctx.db.scheduled_reports().id().find(&id).unwrap().last_error, "API timeout");
    }

    // ──────────────────────────────────────────────────────────────────────
    //  INVOICES (lib.rs)
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_invoice() {
        let ctx = test_ctx();
        create_invoice(&ctx, "t_inv".into(), "cust_1".into(), "tkt_1".into(),
            "Please pay".into(), "Net 30".into(), 1700100000000, "USD".into(), 0.0, 0.0);
        let invoices: Vec<Invoice> = ctx.db.invoices().iter().collect();
        assert_eq!(invoices.len(), 1);
        let i = &invoices[0];
        assert!(i.id.starts_with("inv_"));
        assert_eq!(i.status, "draft");
        assert_eq!(i.invoice_number, 10001);
        assert_eq!(i.currency, "USD");
    }

    #[test]
    fn test_update_invoice_status() {
        let ctx = test_ctx();
        create_invoice(&ctx, "t".into(), "c1".into(), "".into(), "".into(), "".into(), 0, "USD".into(), 0.0, 0.0);
        let id = ctx.db.invoices().iter().next().unwrap().id.clone();
        assert_eq!(ctx.db.invoices().id().find(&id).unwrap().status, "draft");
        update_invoice_status(&ctx, id.clone(), "sent".into());
        assert_eq!(ctx.db.invoices().id().find(&id).unwrap().status, "sent");
    }

    #[test]
    fn test_mark_overdue_invoices() {
        let ctx = test_ctx();
        // Create a past-due sent invoice
        let now = ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000;
        // Can't control timestamp directly in dummy ctx, but we can insert a row
        // with an overdue due_date by using the raw insert pattern via the table accessor
        create_invoice(&ctx, "t".into(), "c1".into(), "".into(), "".into(), "".into(),
            now - 86400000, "USD".into(), 0.0, 0.0); // due yesterday
        let id = ctx.db.invoices().iter().next().unwrap().id.clone();
        update_invoice_status(&ctx, id.clone(), "sent".into());
        mark_overdue_invoices(&ctx);
        let updated = ctx.db.invoices().id().find(&id).unwrap();
        assert_eq!(updated.status, "overdue");
    }

    #[test]
    fn test_add_invoice_line_item() {
        let ctx = test_ctx();
        create_invoice(&ctx, "t".into(), "c1".into(), "".into(), "".into(), "".into(), 0, "USD".into(), 0.0, 0.0);
        let inv_id = ctx.db.invoices().iter().next().unwrap().id.clone();
        add_invoice_line_item(&ctx, inv_id.clone(), "service".into(), "Labor".into(), 2.0, 75.0);
        let items: Vec<InvoiceLineItem> = ctx.db.invoice_line_items().iter().collect();
        assert_eq!(items.len(), 1);
        let item = &items[0];
        assert!(item.id.starts_with("iln_"));
        assert_eq!(item.description, "Labor");
        assert!((item.total - 150.0).abs() < 0.01);

        // Verify invoice totals recalculated
        let inv = ctx.db.invoices().id().find(&inv_id).unwrap();
        assert!((inv.subtotal - 150.0).abs() < 0.01);
        assert!((inv.total - 150.0).abs() < 0.01);
    }

    #[test]
    fn test_delete_invoice_line_item() {
        let ctx = test_ctx();
        create_invoice(&ctx, "t".into(), "c1".into(), "".into(), "".into(), "".into(), 0, "USD".into(), 0.0, 0.0);
        let inv_id = ctx.db.invoices().iter().next().unwrap().id.clone();
        add_invoice_line_item(&ctx, inv_id.clone(), "s".into(), "Item".into(), 1.0, 10.0);
        assert_eq!(ctx.db.invoice_line_items().iter().count(), 1);
        let li_id = ctx.db.invoice_line_items().iter().next().unwrap().id.clone();
        delete_invoice_line_item(&ctx, li_id);
        assert_eq!(ctx.db.invoice_line_items().iter().count(), 0);
    }

    #[test]
    fn test_delete_invoice() {
        let ctx = test_ctx();
        create_invoice(&ctx, "t".into(), "c1".into(), "".into(), "".into(), "".into(), 0, "USD".into(), 0.0, 0.0);
        assert_eq!(ctx.db.invoices().iter().count(), 1);
        let id = ctx.db.invoices().iter().next().unwrap().id.clone();
        delete_invoice(&ctx, id);
        assert_eq!(ctx.db.invoices().iter().count(), 0);
    }

    #[test]
    fn test_set_invoice_tax_rate() {
        let ctx = test_ctx();
        create_invoice(&ctx, "t".into(), "c1".into(), "".into(), "".into(), "".into(), 0, "USD".into(), 0.0, 0.0);
        let inv_id = ctx.db.invoices().iter().next().unwrap().id.clone();
        add_invoice_line_item(&ctx, inv_id.clone(), "s".into(), "Item".into(), 1.0, 100.0);
        set_invoice_tax_rate(&ctx, inv_id.clone(), 8.875);
        let inv = ctx.db.invoices().id().find(&inv_id).unwrap();
        assert!((inv.tax_rate - 8.875).abs() < 0.001);
        assert!((inv.tax_amount - 8.875).abs() < 0.001); // 100 * 8.875 / 100
        assert!((inv.total - 108.875).abs() < 0.001);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  ESTIMATES (lib.rs)
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_create_estimate() {
        let ctx = test_ctx();
        create_estimate(&ctx, "t_est".into(), "cust_1".into(), "tkt_1".into(),
            "Estimate notes".into(), 1700500000000, "USD".into(), 0.0, 0.0);
        let estimates: Vec<Estimate> = ctx.db.estimates().iter().collect();
        assert_eq!(estimates.len(), 1);
        let e = &estimates[0];
        assert!(e.id.starts_with("est_"));
        assert_eq!(e.status, "draft");
        assert_eq!(e.estimate_number, 1001);
    }

    #[test]
    fn test_update_estimate_status() {
        let ctx = test_ctx();
        create_estimate(&ctx, "t".into(), "c1".into(), "".into(), "".into(), 0, "USD".into(), 0.0, 0.0);
        let id = ctx.db.estimates().iter().next().unwrap().id.clone();
        assert_eq!(ctx.db.estimates().id().find(&id).unwrap().status, "draft");
        update_estimate_status(&ctx, id.clone(), "approved".into());
        assert_eq!(ctx.db.estimates().id().find(&id).unwrap().status, "approved");
    }

    #[test]
    fn test_add_estimate_line_item() {
        let ctx = test_ctx();
        create_estimate(&ctx, "t".into(), "c1".into(), "".into(), "".into(), 0, "USD".into(), 0.0, 0.0);
        let est_id = ctx.db.estimates().iter().next().unwrap().id.clone();
        add_estimate_line_item(&ctx, est_id.clone(), "part".into(), "Screen".into(), 1.0, 89.99);
        let items: Vec<EstimateLineItem> = ctx.db.estimate_line_items().iter().collect();
        assert_eq!(items.len(), 1);
        let item = &items[0];
        assert!(item.id.starts_with("eln_"));
        assert!((item.total - 89.99).abs() < 0.01);

        // Verify estimate totals
        let est = ctx.db.estimates().id().find(&est_id).unwrap();
        assert!((est.subtotal - 89.99).abs() < 0.01);
        assert!((est.total - 89.99).abs() < 0.01);
    }

    #[test]
    fn test_delete_estimate() {
        let ctx = test_ctx();
        create_estimate(&ctx, "t".into(), "c1".into(), "".into(), "".into(), 0, "USD".into(), 0.0, 0.0);
        assert_eq!(ctx.db.estimates().iter().count(), 1);
        let id = ctx.db.estimates().iter().next().unwrap().id.clone();
        delete_estimate(&ctx, id);
        assert_eq!(ctx.db.estimates().iter().count(), 0);
    }

    #[test]
    fn test_convert_estimate_to_invoice() {
        let ctx = test_ctx();
        create_estimate(&ctx, "t".into(), "c1".into(), "".into(), "Convert me".into(), 1000, "USD".into(), 0.0, 0.0);
        let est_id = ctx.db.estimates().iter().next().unwrap().id.clone();
        // Add line items
        add_estimate_line_item(&ctx, est_id.clone(), "service".into(), "Repair".into(), 1.0, 200.0);
        add_estimate_line_item(&ctx, est_id.clone(), "part".into(), "Part".into(), 2.0, 25.0);

        assert_eq!(ctx.db.estimates().iter().count(), 1);
        assert_eq!(ctx.db.invoices().iter().count(), 0);
        assert_eq!(ctx.db.estimate_line_items().iter().count(), 2);

        convert_estimate_to_invoice(&ctx, est_id.clone());

        // Estimate should be approved
        let est = ctx.db.estimates().id().find(&est_id).unwrap();
        assert_eq!(est.status, "approved");
        assert!(!est.invoice_id.is_empty());

        // Invoice should exist
        assert_eq!(ctx.db.invoices().iter().count(), 1);
        let inv = ctx.db.invoices().iter().next().unwrap();
        assert_eq!(inv.customer_id, "c1");
        assert!((inv.subtotal - 250.0).abs() < 0.01);

        // Line items should be copied
        assert_eq!(ctx.db.invoice_line_items().iter().count(), 2);
        let copied: Vec<InvoiceLineItem> = ctx.db.invoice_line_items().iter()
            .filter(|i| i.invoice_id == inv.id).collect();
        assert_eq!(copied.len(), 2);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  MARK_OVERDUE: edge case (no overdue invoices)
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_mark_overdue_no_invoices_doesnt_panic() {
        let ctx = test_ctx();
        mark_overdue_invoices(&ctx); // Should not panic with empty table
    }

    // ──────────────────────────────────────────────────────────────────────
    //  NONE-EXISTENT REDUCER SAFETY: batch
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_all_nonexistent_operations_dont_panic() {
        let ctx = test_ctx();
        // These should all be no-ops, not panics
        create_tenant(&ctx, "Isolated".into(), "isolated".into());
        let _ = ctx.db.tenants().iter().next().unwrap().id.clone();

        delete_customer(&ctx, "cust_nope".into());
        delete_payment(&ctx, "pmt_nope".into());
        delete_product(&ctx, "prod_nope".into());
        delete_ticket(&ctx, "tkt_nope".into());
        delete_invoice(&ctx, "inv_nope".into());
        delete_estimate(&ctx, "est_nope".into());
        delete_tenant(&ctx, "tnt_nope".into());
        delete_user(&ctx, "user_nope".into());
        delete_appointment(&ctx, "appt_nope".into());
        delete_webhook_subscription(&ctx, "whk_nope".into());
        delete_payment_method(&ctx, "pm_nope".into());
        delete_recurring_invoice_rule(&ctx, "rir_nope".into());
        delete_scheduled_report(&ctx, "srpt_nope".into());
        delete_custom_field_definition(&ctx, "cfd_nope".into());
        delete_invoice_line_item(&ctx, "iln_nope".into());
        delete_inventory_adjustment(&ctx, "adj_nope".into());
        delete_checklist_template(&ctx, "clt_nope".into());
        delete_counter_sale(&ctx, "pos_nope".into());
        let _ = delete_customer_geolocation(&ctx, "cust_nope".into());
        let _ = delete_ticket_checklist(&ctx, "tkt_nope".into());
        let _ = set_custom_field_value(&ctx, "e".into(), "f".into(), "v".into(), "t_nope".into());
        let _ = delete_custom_field_value(&ctx, "e".into(), "f".into());
        // Untested reducers safety
        set_user_pin(&ctx, "user_nope".into(), "1234".into());
        upsert_user_settings(&ctx, "user_nope".into(), "dark".into(), "new".into());
        delete_user_settings(&ctx, "user_nope".into());
        update_product_quantity(&ctx, "prod_nope".into(), 0.0);
        import_customer(&ctx, "t".into(), "cust_nope".into(), "N".into(), "N".into(), "n@t.com".into(), "".into(), "".into(), "".into(), "".into(), "".into(), "".into(), "".into(), "".into(), "".into(), "".into(), 0, 0);
        import_product(&ctx, "t".into(), "prod_nope".into(), "N".into(), "N".into(), "".into(), "".into(), "".into(), 0.0, 0.0, 0.0, 0.0, 0.0, "".into(), true, 0, 0);
        let _ = delete_po_line_item(&ctx, "po_nope".into(), "poli_nope".into());
        let _ = submit_for_approval(&ctx, "po_nope".into());
        let _ = approve_po(&ctx, "po_nope".into(), "u".into());
        let _ = reject_po(&ctx, "po_nope".into());
        let _ = receive_po_item(&ctx, "poli_nope".into(), 0.0);
        let _ = delete_purchase_order(&ctx, "po_nope".into());
        delete_ticket_timer(&ctx, "tmr_nope".into());
        generate_recurring_invoices(&ctx);

        // No crash = success
    }

    // ──────────────────────────────────────────────────────────────────────
    //  CUSTOMER: import_customer
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_import_customer() {
        let ctx = test_ctx();
        import_customer(
            &ctx,
            "t_imp".into(),
            "cust_imported_1".into(),
            "Imported".into(),
            "User".into(),
            "imported@test.com".into(),
            "555-0001".into(),
            "555-0002".into(),
            "123 Main St".into(),
            "".into(),
            "Portland".into(),
            "OR".into(),
            "97201".into(),
            "Acme Corp".into(),
            "Bulk import".into(),
            "".into(),
            1000000000000,
            1000000000000,
        );
        let customers: Vec<Customer> = ctx.db.customer().iter().collect();
        assert_eq!(customers.len(), 1);
        let c = &customers[0];
        assert_eq!(c.id, "cust_imported_1");
        assert_eq!(c.first_name, "Imported");
        assert_eq!(c.created_at, 1000000000000);
        assert_eq!(c.updated_at, 1000000000000);
        assert_eq!(c.company, "Acme Corp");
        assert_eq!(c.city, "Portland");
    }

    // ──────────────────────────────────────────────────────────────────────
    //  PRODUCT: update_product_quantity, import_product
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_update_product_quantity() {
        let ctx = test_ctx();
        create_product(&ctx, "t_pq".into(), "Widget".into(), "WDG".into(),
            "".into(), "".into(), "Parts".into(), 10.0, 5.0, 50.0, 5.0, "A1".into());
        let pid = ctx.db.products().iter().next().unwrap().id.clone();
        assert_eq!(ctx.db.products().id().find(&pid).unwrap().quantity_on_hand, 50.0);
        update_product_quantity(&ctx, pid.clone(), 30.0);
        let updated = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated.quantity_on_hand, 30.0);
        assert_eq!(updated.quantity_available, 30.0);
    }

    #[test]
    fn test_update_nonexistent_product_quantity_doesnt_panic() {
        let ctx = test_ctx();
        update_product_quantity(&ctx, "prod_nope".into(), 99.0);
        assert_eq!(ctx.db.products().iter().count(), 0);
    }

    #[test]
    fn test_import_product() {
        let ctx = test_ctx();
        import_product(&ctx, "t_ip".into(), "prod_imported_1".into(),
            "Imported Widget".into(), "IMP-001".into(), "123456789".into(),
            "High quality widget".into(), "Gadgets".into(),
            29.99, 12.00, 100.0, 10.0, 5.0, "B2".into(), true, 2000000000000, 2000000000000);
        let products_list: Vec<Product> = ctx.db.products().iter().collect();
        assert_eq!(products_list.len(), 1);
        let p = &products_list[0];
        assert_eq!(p.id, "prod_imported_1");
        assert_eq!(p.name, "Imported Widget");
        assert_eq!(p.price, 29.99);
        assert_eq!(p.quantity_on_hand, 100.0);
        assert_eq!(p.quantity_committed, 10.0);
        assert_eq!(p.quantity_available, 90.0);
        assert_eq!(p.created_at, 2000000000000);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  PURCHASE ORDER LIFECYCLE
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_po_submit_for_approval() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "Vendor Co".into(), "Urgent".into(), "USD".into(), 0.0);
        let po = ctx.db.purchase_order().iter().next().unwrap();
        let poid = po.id.clone();
        assert_eq!(po.status, "draft");
        submit_for_approval(&ctx, poid.clone());
        assert_eq!(ctx.db.purchase_order().id().find(&poid).unwrap().status, "pending_approval");
    }

    #[test]
    fn test_po_submit_for_approval_from_non_draft_is_noop() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t".into(), "V".into(), "".into(), "USD".into(), 0.0);
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        submit_for_approval(&ctx, poid.clone());
        assert_eq!(ctx.db.purchase_order().id().find(&poid).unwrap().status, "pending_approval");
        // Second submit should be no-op (already pending_approval)
        submit_for_approval(&ctx, poid);
        // No crash = success
    }

    #[test]
    fn test_po_approve() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t".into(), "V".into(), "".into(), "USD".into(), 0.0);
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        submit_for_approval(&ctx, poid.clone());
        approve_po(&ctx, poid.clone(), "user_admin".into());
        let po = ctx.db.purchase_order().id().find(&poid).unwrap();
        assert_eq!(po.status, "approved");
        assert_eq!(po.approved_by, "user_admin");
        assert!(po.approved_at > 0);
    }

    #[test]
    fn test_po_approve_from_draft_is_noop() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t".into(), "V".into(), "".into(), "USD".into(), 0.0);
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        approve_po(&ctx, poid, "user_admin".into());
        // Should stay draft
        assert_eq!(ctx.db.purchase_order().iter().next().unwrap().status, "draft");
    }

    #[test]
    fn test_po_reject() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t".into(), "V".into(), "".into(), "USD".into(), 0.0);
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        submit_for_approval(&ctx, poid.clone());
        reject_po(&ctx, poid.clone());
        assert_eq!(ctx.db.purchase_order().id().find(&poid).unwrap().status, "draft");
    }

    #[test]
    fn test_po_reject_from_draft_is_noop() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t".into(), "V".into(), "".into(), "USD".into(), 0.0);
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        reject_po(&ctx, poid);
        // Should stay draft
        assert_eq!(ctx.db.purchase_order().iter().next().unwrap().status, "draft");
    }

    #[test]
    fn test_po_add_and_delete_line_item() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t".into(), "V".into(), "".into(), "USD".into(), 0.0);
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        // Add a line item
        add_po_line_item(&ctx, poid.clone(), "prod_1".into(), "Cable".into(), 10.0, 5.0);
        use crate::purchase_order::purchase_order_line_item;
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 1);
        let item = ctx.db.purchase_order_line_item().iter().next().unwrap();
        assert_eq!(item.description, "Cable");
        assert!((item.total - 50.0).abs() < 0.01);
        // PO totals should be recalculated
        let po = ctx.db.purchase_order().id().find(&poid).unwrap();
        assert!((po.subtotal - 50.0).abs() < 0.01);
        // Delete the line item
        let item_id = item.id.clone();
        delete_po_line_item(&ctx, poid.clone(), item_id);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 0);
        // PO should recalc to zero
        let po2 = ctx.db.purchase_order().id().find(&poid).unwrap();
        assert!((po2.subtotal - 0.0).abs() < 0.01);
    }

    #[test]
    fn test_po_receive_item() {
        let ctx = test_ctx();
        // Create a product to receive against
        create_product(&ctx, "t_rcv".into(), "RAM Stick".into(), "RAM-8GB".into(),
            "".into(), "".into(), "Parts".into(), 49.99, 25.0, 5.0, 2.0, "C3".into());
        let prod = ctx.db.products().iter().next().unwrap();
        let pid = prod.id.clone();
        assert_eq!(prod.quantity_on_hand, 5.0);
        // Create PO and add line item referencing the product
        create_purchase_order(&ctx, "t_rcv".into(), "MemSupplier".into(), "".into(), "USD".into(), 0.0);
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(&ctx, poid.clone(), pid.clone(), "8GB DDR4".into(), 10.0, 30.0);
        let item = ctx.db.purchase_order_line_item().iter().next().unwrap();
        let item_id = item.id.clone();
        assert_eq!(item.received_quantity, 0.0);
        // Receive 5 units
        receive_po_item(&ctx, item_id.clone(), 5.0);
        // Line item should show received
        let updated_item = ctx.db.purchase_order_line_item().id().find(&item_id).unwrap();
        assert_eq!(updated_item.received_quantity, 5.0);
        // Product stock should increase
        let updated_prod = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated_prod.quantity_on_hand, 10.0);
        // Inventory adjustment should be created
        assert_eq!(ctx.db.inventory_adjustment().iter().count(), 1);
        let adj = ctx.db.inventory_adjustment().iter().next().unwrap();
        assert_eq!(adj.reason, "received");
        // PO status should be "partial"
        let po = ctx.db.purchase_order().id().find(&poid).unwrap();
        assert_eq!(po.status, "partial");
    }

    #[test]
    fn test_po_receive_full_quantity() {
        let ctx = test_ctx();
        create_product(&ctx, "t".into(), "P".into(), "P".into(), "".into(),
            "".into(), "".into(), 1.0, 0.5, 0.0, 0.0, "".into());
        let pid = ctx.db.products().iter().next().unwrap().id.clone();
        create_purchase_order(&ctx, "t".into(), "V".into(), "".into(), "USD".into(), 0.0);
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(&ctx, poid.clone(), pid, "Item".into(), 3.0, 10.0);
        let item_id = ctx.db.purchase_order_line_item().iter().next().unwrap().id.clone();
        receive_po_item(&ctx, item_id, 3.0);
        // PO status should be "received" when fully received
        let po = ctx.db.purchase_order().id().find(&poid).unwrap();
        assert_eq!(po.status, "received");
    }

    #[test]
    fn test_delete_purchase_order() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t".into(), "V".into(), "".into(), "USD".into(), 0.0);
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        // Add line items
        add_po_line_item(&ctx, poid.clone(), "p1".into(), "Item A".into(), 2.0, 10.0);
        add_po_line_item(&ctx, poid.clone(), "p2".into(), "Item B".into(), 1.0, 20.0);
        assert_eq!(ctx.db.purchase_order().iter().count(), 1);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 2);
        delete_purchase_order(&ctx, poid);
        assert_eq!(ctx.db.purchase_order().iter().count(), 0);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  TICKET: delete_ticket_timer
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_delete_ticket_timer() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t_tmr".into(), "c1".into(), "Timer test delete".into(), "".into(), "".into(), "".into(), "".into(), "low".into());
        let tid = ctx.db.ticket().iter().next().unwrap().id.clone();
        start_ticket_timer(&ctx, tid, "user_1".into());
        use crate::ticket::ticket_timer;
        assert_eq!(ctx.db.ticket_timer().iter().count(), 1);
        let timer_id = ctx.db.ticket_timer().iter().next().unwrap().id.clone();
        delete_ticket_timer(&ctx, timer_id);
        assert_eq!(ctx.db.ticket_timer().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_ticket_timer_doesnt_panic() {
        let ctx = test_ctx();
        delete_ticket_timer(&ctx, "tmr_nonexistent".into());
        assert_eq!(ctx.db.ticket_timer().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  USER: set_user_pin, upsert_user_settings, delete_user_settings
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_set_user_pin() {
        let ctx = test_ctx();
        create_user(&ctx, "pin_user".into(), "pin@test.com".into(), "front_desk".into());
        let uid = ctx.db.user().iter().next().unwrap().id.clone();
        assert!(ctx.db.user().id().find(&uid).unwrap().pin.is_empty());
        set_user_pin(&ctx, uid.clone(), "4321".into());
        assert_eq!(ctx.db.user().id().find(&uid).unwrap().pin, "4321");
    }

    #[test]
    fn test_set_nonexistent_user_pin_doesnt_panic() {
        let ctx = test_ctx();
        set_user_pin(&ctx, "user_nope".into(), "0000".into());
        assert_eq!(ctx.db.user().iter().count(), 0);
    }

    #[test]
    fn test_upsert_user_settings_create() {
        let ctx = test_ctx();
        create_user(&ctx, "settings_test".into(), "s@test.com".into(), "tech".into());
        let uid = ctx.db.user().iter().next().unwrap().id.clone();
        upsert_user_settings(&ctx, uid.clone(), "dark".into(), "in_progress".into());
        use crate::user::user_settings;
        let settings: Vec<UserSettings> = ctx.db.user_settings().iter().collect();
        assert_eq!(settings.len(), 1);
        let s = &settings[0];
        assert_eq!(s.user_id, uid);
        assert_eq!(s.theme, "dark");
        assert_eq!(s.default_ticket_status, "in_progress");
        assert!(s.created_at > 0);
        assert_eq!(s.created_at, s.updated_at);
    }

    #[test]
    fn test_upsert_user_settings_update() {
        let ctx = test_ctx();
        create_user(&ctx, "upd_test".into(), "upd@test.com".into(), "admin".into());
        let uid = ctx.db.user().iter().next().unwrap().id.clone();
        upsert_user_settings(&ctx, uid.clone(), "light".into(), "new".into());
        let original = ctx.db.user_settings().user_id().find(&uid).unwrap();
        assert_eq!(original.theme, "light");
        // Update
        upsert_user_settings(&ctx, uid.clone(), "dark".into(), "in_progress".into());
        let updated = ctx.db.user_settings().user_id().find(&uid).unwrap();
        assert_eq!(updated.theme, "dark");
        assert_eq!(updated.default_ticket_status, "in_progress");
        assert_eq!(updated.user_id, uid);
        assert!(updated.updated_at >= original.updated_at);
        assert_eq!(ctx.db.user_settings().iter().count(), 1); // still 1 row
    }

    #[test]
    fn test_delete_user_settings() {
        let ctx = test_ctx();
        create_user(&ctx, "del_settings".into(), "ds@test.com".into(), "tech".into());
        let uid = ctx.db.user().iter().next().unwrap().id.clone();
        upsert_user_settings(&ctx, uid.clone(), "dark".into(), "new".into());
        assert_eq!(ctx.db.user_settings().iter().count(), 1);
        delete_user_settings(&ctx, uid);
        assert_eq!(ctx.db.user_settings().iter().count(), 0);
    }

    // ──────────────────────────────────────────────────────────────────────
    //  RECURRING INVOICE: generate_recurring_invoices
    // ──────────────────────────────────────────────────────────────────────

    #[test]
    fn test_generate_recurring_invoices() {
        let ctx = test_ctx();
        // Create a recurring rule with past-due next_generation_date
        let now = ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000;
        let items = r#"[{"description":"Monthly rent","quantity":1,"unit_price":500}]"#;
        create_recurring_invoice_rule(&ctx, "t_gr".into(), "cust_1".into(),
            "Monthly Rent".into(), "monthly".into(), 1, 15,
            items.into(), "USD".into(), now - 1000); // due now
        // Generate invoices
        assert_eq!(ctx.db.invoices().iter().count(), 0);
        generate_recurring_invoices(&ctx);
        // Should have created 1 invoice
        assert_eq!(ctx.db.invoices().iter().count(), 1);
        let inv = ctx.db.invoices().iter().next().unwrap();
        assert_eq!(inv.tenant_id, "t_gr");
        assert_eq!(inv.customer_id, "cust_1");
        assert!(inv.notes.contains("Monthly Rent"));
        // Line items should be copied
        assert_eq!(ctx.db.invoice_line_items().iter().count(), 1);
        let li = ctx.db.invoice_line_items().iter().next().unwrap();
        assert_eq!(li.description, "Monthly rent");
        assert!((li.total - 500.0).abs() < 0.01);
        // Rule's next_generation_date should be updated
        use crate::recurring_invoice_rules;
        let rule = ctx.db.recurring_invoice_rules().iter().next().unwrap();
        assert!(rule.next_generation_date > now - 1000);
        assert_eq!(rule.last_generated_date, now);
    }

    #[test]
    fn test_generate_recurring_no_due_rules() {
        let ctx = test_ctx();
        // Create a rule with future date
        let far_future = 9999999999999999;
        create_recurring_invoice_rule(&ctx, "t".into(), "c1".into(), "Future".into(),
            "monthly".into(), 1, 15, "[]".into(), "USD".into(), far_future);
        generate_recurring_invoices(&ctx);
        assert_eq!(ctx.db.invoices().iter().count(), 0);
    }

    #[test]
    fn test_generate_recurring_paused_rule_skipped() {
        let ctx = test_ctx();
        let now = ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000;
        create_recurring_invoice_rule(&ctx, "t".into(), "c1".into(), "Paused".into(),
            "monthly".into(), 1, 15, "[]".into(), "USD".into(), now - 1000);
        // Pause it
        let id = ctx.db.recurring_invoice_rules().iter().next().unwrap().id.clone();
        update_recurring_invoice_rule(&ctx, id, "Paused".into(), "monthly".into(), 1, 15, "[]".into(), "USD".into(), now - 1000, "paused".into());
        generate_recurring_invoices(&ctx);
        assert_eq!(ctx.db.invoices().iter().count(), 0);
    }

    #[test]
    fn test_generate_recurring_empty_customer_skipped() {
        let ctx = test_ctx();
        let now = ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000;
        // Rule with empty customer_id
        create_recurring_invoice_rule(&ctx, "t".into(), "".into(), "NoCust".into(),
            "monthly".into(), 1, 15, "[]".into(), "USD".into(), now - 1000);
        generate_recurring_invoices(&ctx);
        assert_eq!(ctx.db.invoices().iter().count(), 0);
    }
}
