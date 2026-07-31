#[cfg(test)]
mod tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

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
        delete_recurring_invoice_rule(&ctx, "rir_nope".into(), "t".into());
        delete_scheduled_report(&ctx, "srpt_nope".into());
        delete_custom_field_definition(&ctx, "cfd_nope".into());
        delete_invoice_line_item(&ctx, "iln_nope".into());
        delete_inventory_adjustment(&ctx, "adj_nope".into());
        delete_checklist_template(&ctx, "clt_nope".into());
        delete_counter_sale(&ctx, "pos_nope".into());
        delete_customer_geolocation(&ctx, "cust_nope".into());
        delete_ticket_checklist(&ctx, "tkt_nope".into());
        let _ = set_custom_field_value(&ctx, "e".into(), "f".into(), "v".into(), "t_nope".into());
        delete_custom_field_value(&ctx, "e".into(), "f".into());
        // Untested reducers safety
        set_user_pin(&ctx, "user_nope".into(), "1234".into());
        upsert_user_settings(&ctx, "user_nope".into(), "dark".into(), "new".into());
        delete_user_settings(&ctx, "user_nope".into());
        update_product_quantity(&ctx, "prod_nope".into(), 0.0);
        import_customer(
            &ctx,
            "t".into(),
            "cust_nope".into(),
            "N".into(),
            "N".into(),
            "n@t.com".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            0,
            0,
        );
        import_product(
            &ctx,
            "t".into(),
            "prod_nope".into(),
            "N".into(),
            "N".into(),
            "".into(),
            "".into(),
            "".into(),
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            "".into(),
            true,
            0,
            0,
        );
        delete_po_line_item(&ctx, "po_nope".into(), "poli_nope".into());
        submit_for_approval(&ctx, "po_nope".into());
        approve_po(&ctx, "po_nope".into(), "u".into());
        reject_po(&ctx, "po_nope".into());
        receive_po_item(&ctx, "poli_nope".into(), 0.0);
        delete_purchase_order(&ctx, "po_nope".into());
        delete_ticket_timer(&ctx, "tmr_nope".into());
        generate_recurring_invoices(&ctx, "t".into());

        // No crash = success
    }
}
