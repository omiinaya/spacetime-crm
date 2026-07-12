//! Integration-style unit tests for STDB reducers.
//!
//! Each test creates isolated dummy ReducerContexts, runs reducers,
//! and asserts table state. Follows the customer_test pattern.

#[cfg(test)]
mod tests {
    use crate::*;
    // Import accessor traits for STDB table access
    use crate::product::products;
    use crate::purchase_order::purchase_order;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    // ──────────────────────────────────────────────
    //  TICKET
    // ──────────────────────────────────────────────

    #[test]
    fn test_create_ticket() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "tenant_t".into(),
            "cust_1".into(),
            "Broken screen".into(),
            "Cracked glass".into(),
            "iPhone".into(),
            "15".into(),
            "SN001".into(),
            "high".into(),
        );
        use crate::ticket::ticket;
        let tickets: Vec<Ticket> = ctx.db.ticket().iter().collect();
        assert_eq!(tickets.len(), 1);
        let t = &tickets[0];
        assert!(t.id.starts_with("tkt_"));
        assert_eq!(t.tenant_id, "tenant_t");
        assert_eq!(t.title, "Broken screen");
        assert_eq!(t.status, "new");
        assert_eq!(t.priority, "high");
        assert!(t.created_at > 0);
        assert_eq!(t.created_at, t.updated_at);
    }

    #[test]
    fn test_update_ticket_status() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Fix".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        use crate::ticket::ticket;
        let t = ctx.db.ticket().iter().next().unwrap();
        let id = t.id.clone();
        assert_eq!(t.status, "new");
        update_ticket_status(&ctx, id.clone(), "in_progress".into());
        let updated = ctx.db.ticket().id().find(&id).unwrap();
        assert_eq!(updated.status, "in_progress");
    }

    #[test]
    fn test_assign_ticket() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Assign test".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "medium".into(),
        );
        use crate::ticket::ticket;
        let t = ctx.db.ticket().iter().next().unwrap();
        let id = t.id.clone();
        assert!(t.assigned_user_id.is_empty());
        assign_ticket(&ctx, id.clone(), "user_tech".into());
        let updated = ctx.db.ticket().id().find(&id).unwrap();
        assert_eq!(updated.assigned_user_id, "user_tech");
    }

    #[test]
    fn test_add_ticket_note() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Note test".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        use crate::ticket::ticket;
        let t = ctx.db.ticket().iter().next().unwrap();
        let tid = t.id.clone();
        add_ticket_note(
            &ctx,
            tid.clone(),
            "Bob".into(),
            "Checked device".into(),
            false,
        );
        use crate::ticket::ticket_note;
        let notes: Vec<TicketNote> = ctx.db.ticket_note().iter().collect();
        assert_eq!(notes.len(), 1);
        let n = &notes[0];
        assert!(n.id.starts_with("tnote_"));
        assert_eq!(n.ticket_id, tid);
        assert_eq!(n.author, "Bob");
        assert_eq!(n.content, "Checked device");
    }

    #[test]
    fn test_delete_ticket() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Delete me".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        use crate::ticket::ticket;
        assert_eq!(ctx.db.ticket().iter().count(), 1);
        let id = ctx.db.ticket().iter().next().unwrap().id.clone();
        delete_ticket(&ctx, id);
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_ticket_timer_lifecycle() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Timer test".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        use crate::ticket::ticket;
        let t = ctx.db.ticket().iter().next().unwrap();
        let tid = t.id.clone();
        start_ticket_timer(&ctx, tid.clone(), "user_1".into());
        use crate::ticket::ticket_timer;
        let timers: Vec<TicketTimer> = ctx.db.ticket_timer().iter().collect();
        assert_eq!(timers.len(), 1);
        let tmr = &timers[0];
        assert!(tmr.running);
        stop_ticket_timer(&ctx, tmr.id.clone());
        let stopped = ctx.db.ticket_timer().id().find(&tmr.id).unwrap();
        assert!(!stopped.running);
    }

    #[test]
    fn test_update_nonexistent_ticket_doesnt_panic() {
        let ctx = test_ctx();
        update_ticket_status(&ctx, "tkt_nonexistent".into(), "resolved".into());
        use crate::ticket::ticket;
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    // ──────────────────────────────────────────────
    //  PAYMENT
    // ──────────────────────────────────────────────

    #[test]
    fn test_record_payment() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "tenant_p".into(),
            "inv_1".into(),
            "cust_1".into(),
            150.00,
            "cash".into(),
            "REF-001".into(),
            "Walk-in payment".into(),
            "USD".into(),
        );
        use crate::payment::payment;
        let payments: Vec<Payment> = ctx.db.payment().iter().collect();
        assert_eq!(payments.len(), 1);
        let p = &payments[0];
        assert_eq!(p.amount, 150.00);
        assert_eq!(p.method, "cash");
        assert_eq!(p.currency, "USD");
    }

    #[test]
    fn test_delete_payment() {
        let ctx = test_ctx();
        record_payment(
            &ctx,
            "t".into(),
            "i".into(),
            "c".into(),
            50.0,
            "cash".into(),
            "".into(),
            "".into(),
            "USD".into(),
        );
        use crate::payment::payment;
        assert_eq!(ctx.db.payment().iter().count(), 1);
        let id = ctx.db.payment().iter().next().unwrap().id.clone();
        delete_payment(&ctx, id);
        assert_eq!(ctx.db.payment().iter().count(), 0);
    }

    // ──────────────────────────────────────────────
    //  PRODUCT
    // ──────────────────────────────────────────────

    #[test]
    fn test_create_product() {
        let ctx = test_ctx();
        create_product(
            &ctx,
            "tenant_pr".into(),
            "Screen".into(),
            "SCR-001".into(),
            "".into(),
            "".into(),
            "Parts".into(),
            29.99,
            12.50,
            50.0,
            5.0,
            "Aisle-3".into(),
        );
        let products_list: Vec<Product> = ctx.db.products().iter().collect();
        assert_eq!(products_list.len(), 1);
        let p = &products_list[0];
        assert_eq!(p.name, "Screen");
        assert_eq!(p.sku, "SCR-001");
        assert_eq!(p.price, 29.99);
    }

    #[test]
    fn test_update_product() {
        let ctx = test_ctx();
        create_product(
            &ctx,
            "t".into(),
            "Old".into(),
            "OLD-001".into(),
            "".into(),
            "".into(),
            "".into(),
            10.0,
            5.0,
            10.0,
            0.0,
            "".into(),
        );
        let p = ctx.db.products().iter().next().unwrap();
        let pid = p.id.clone();
        update_product(
            &ctx,
            pid.clone(),
            "New Name".into(),
            "NEW-001".into(),
            "".into(),
            "desc".into(),
            "cat".into(),
            25.0,
            8.0,
            5.0,
            "B-12".into(),
        );
        let updated = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated.name, "New Name");
    }

    #[test]
    fn test_delete_product() {
        let ctx = test_ctx();
        create_product(
            &ctx,
            "t".into(),
            "Del".into(),
            "DEL".into(),
            "".into(),
            "".into(),
            "".into(),
            1.0,
            0.5,
            5.0,
            0.0,
            "".into(),
        );
        assert_eq!(ctx.db.products().iter().count(), 1);
        let id = ctx.db.products().iter().next().unwrap().id.clone();
        delete_product(&ctx, id);
        assert_eq!(ctx.db.products().iter().count(), 0);
    }

    // ──────────────────────────────────────────────
    //  PURCHASE ORDER
    // ──────────────────────────────────────────────

    #[test]
    fn test_create_purchase_order() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "tenant_po".into(),
            "vendor_1".into(),
            "notes".into(),
            "USD".into(),
        );
        let pos: Vec<PurchaseOrder> = ctx.db.purchase_order().iter().collect();
        assert_eq!(pos.len(), 1);
        let po = &pos[0];
        assert_eq!(po.vendor_name, "vendor_1");
        assert_eq!(po.status, "draft");
    }

    #[test]
    fn test_update_po_status() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t".into(), "v1".into(), "".into(), "USD".into());
        let po = ctx.db.purchase_order().iter().next().unwrap();
        let poid = po.id.clone();
        assert_eq!(po.status, "draft");
        update_po_status(&ctx, poid.clone(), "sent".into());
        let updated = ctx.db.purchase_order().id().find(&poid).unwrap();
        assert_eq!(updated.status, "sent");
    }

    // ──────────────────────────────────────────────
    //  TENANT ISOLATION
    // ──────────────────────────────────────────────

    #[test]
    fn test_ticket_tenant_isolation() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t_a".into(),
            "c1".into(),
            "Tkt A".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        create_ticket(
            &ctx,
            "t_b".into(),
            "c2".into(),
            "Tkt B".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "high".into(),
        );
        use crate::ticket::ticket;
        let tickets: Vec<Ticket> = ctx
            .db
            .ticket()
            .iter()
            .filter(|t| t.tenant_id == "t_a")
            .collect();
        assert_eq!(tickets.len(), 1);
        assert_eq!(tickets[0].title, "Tkt A");
    }

    // ──────────────────────────────────────────────
    //  EDGE CASES
    // ──────────────────────────────────────────────

    #[test]
    fn test_assign_nonexistent_ticket_doesnt_panic() {
        let ctx = test_ctx();
        assign_ticket(&ctx, "tkt_nonexistent".into(), "user_x".into());
        use crate::ticket::ticket;
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_payment_doesnt_panic() {
        let ctx = test_ctx();
        use crate::payment::payment;
        delete_payment(&ctx, "pmt_nonexistent".into());
        assert_eq!(ctx.db.payment().iter().count(), 0);
    }

    #[test]
    fn test_timer_note_derives_tenant_from_ticket() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t_derived".into(),
            "c1".into(),
            "Derive test".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        use crate::ticket::ticket;
        let t = ctx.db.ticket().iter().next().unwrap();
        let tid = t.id.clone();
        add_ticket_note(&ctx, tid.clone(), "Tech".into(), "Noted".into(), false);
        use crate::ticket::ticket_note;
        let note = ctx.db.ticket_note().iter().next().unwrap();
        assert_eq!(note.tenant_id, "t_derived");
    }

    // ──────────────────────────────────────────────
    //  RECURRING INVOICE RULES
    // ──────────────────────────────────────────────

    #[test]
    fn test_create_recurring_invoice_rule() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(
            &ctx,
            "t_rinv".into(),
            "Monthly".into(),
            "monthly".into(),
            1,
            30,
            r#"[{"item_type":"labor","description":"Support","quantity":1,"unit_price":100}]"#
                .into(),
            1000000,
        );
        use crate::recurring_invoice_rules;
        let rules: Vec<RecurringInvoiceRule> = ctx.db.recurring_invoice_rules().iter().collect();
        assert_eq!(rules.len(), 1);
        assert_eq!(rules[0].name, "Monthly");
        assert_eq!(rules[0].frequency, "monthly");
    }

    #[test]
    fn test_update_recurring_invoice_rule() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(
            &ctx,
            "t".into(),
            "Original".into(),
            "weekly".into(),
            1,
            14,
            "[]".into(),
            0,
        );
        use crate::recurring_invoice_rules;
        let rule = ctx.db.recurring_invoice_rules().iter().next().unwrap();
        let id = rule.id.clone();
        update_recurring_invoice_rule(
            &ctx,
            id.clone(),
            "Updated".into(),
            "monthly".into(),
            2,
            30,
            "[]".into(),
            2000000,
            "active".into(),
        );
        let updated = ctx.db.recurring_invoice_rules().id().find(&id).unwrap();
        assert_eq!(updated.name, "Updated");
        assert_eq!(updated.frequency, "monthly");
    }

    #[test]
    fn test_delete_nonexistent_recurring_invoice_rule_doesnt_panic() {
        let ctx = test_ctx();
        delete_recurring_invoice_rule(&ctx, "nonexistent".into());
        use crate::recurring_invoice_rules;
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 0);
    }

    // ──────────────────────────────────────────────
    //  SAVED PAYMENT METHODS
    // ──────────────────────────────────────────────

    #[test]
    fn test_save_payment_method() {
        let ctx = test_ctx();
        save_payment_method(
            &ctx,
            "t_pm".into(),
            "cust_1".into(),
            "pm_stripe123".into(),
            "Visa".into(),
            "4242".into(),
            12,
            2026,
        );
        use crate::saved_payment_methods;
        let methods: Vec<SavedPaymentMethod> = ctx.db.saved_payment_methods().iter().collect();
        assert_eq!(methods.len(), 1);
        assert_eq!(methods[0].brand, "Visa");
        assert!(methods[0].is_default); // first method is default
    }

    #[test]
    fn test_set_default_payment_method() {
        let ctx = test_ctx();
        save_payment_method(
            &ctx,
            "t".into(),
            "cust_1".into(),
            "pm1".into(),
            "Visa".into(),
            "4242".into(),
            12,
            2026,
        );
        save_payment_method(
            &ctx,
            "t".into(),
            "cust_1".into(),
            "pm2".into(),
            "MC".into(),
            "5555".into(),
            6,
            2025,
        );
        use crate::saved_payment_methods;
        let first = ctx.db.saved_payment_methods().iter().next().unwrap();
        let id = first.id.clone();
        set_default_payment_method(&ctx, id.clone(), "cust_1".into());
        let updated = ctx.db.saved_payment_methods().id().find(&id).unwrap();
        assert!(updated.is_default);
    }

    #[test]
    fn test_delete_nonexistent_payment_method_doesnt_panic() {
        let ctx = test_ctx();
        delete_payment_method(&ctx, "nonexistent".into());
        use crate::saved_payment_methods;
        assert_eq!(ctx.db.saved_payment_methods().iter().count(), 0);
    }

    // ──────────────────────────────────────────────
    //  SCHEDULED REPORTS
    // ──────────────────────────────────────────────

    #[test]
    fn test_create_scheduled_report() {
        let ctx = test_ctx();
        create_scheduled_report(
            &ctx,
            "t_rep".into(),
            "Weekly Report".into(),
            "tickets".into(),
            "weekly".into(),
            "{}".into(),
            "[]".into(),
            "{}".into(),
            1000000,
        );
        use crate::scheduled_reports;
        let reports: Vec<ScheduledReport> = ctx.db.scheduled_reports().iter().collect();
        assert_eq!(reports.len(), 1);
        assert_eq!(reports[0].name, "Weekly Report");
    }

    #[test]
    fn test_update_scheduled_report() {
        let ctx = test_ctx();
        create_scheduled_report(
            &ctx,
            "t".into(),
            "Old".into(),
            "tickets".into(),
            "daily".into(),
            "{}".into(),
            "[]".into(),
            "{}".into(),
            0,
        );
        use crate::scheduled_reports;
        let report = ctx.db.scheduled_reports().iter().next().unwrap();
        let id = report.id.clone();
        update_scheduled_report(
            &ctx,
            id.clone(),
            "New".into(),
            "invoices".into(),
            "weekly".into(),
            "{}".into(),
            "[]".into(),
            "{}".into(),
            2000000,
            true,
        );
        let updated = ctx.db.scheduled_reports().id().find(&id).unwrap();
        assert_eq!(updated.name, "New");
        assert_eq!(updated.report_type, "invoices");
    }

    #[test]
    fn test_mark_report_run() {
        let ctx = test_ctx();
        create_scheduled_report(
            &ctx,
            "t".into(),
            "R".into(),
            "tickets".into(),
            "daily".into(),
            "{}".into(),
            "[]".into(),
            "{}".into(),
            0,
        );
        use crate::scheduled_reports;
        let report = ctx.db.scheduled_reports().iter().next().unwrap();
        let id = report.id.clone();
        mark_report_run(&ctx, id.clone(), 5000000);
        let updated = ctx.db.scheduled_reports().id().find(&id).unwrap();
        assert_eq!(updated.next_run_at, 5000000);
        assert_eq!(updated.last_run_at, 5000000);
    }

    #[test]
    fn test_mark_report_error() {
        let ctx = test_ctx();
        create_scheduled_report(
            &ctx,
            "t".into(),
            "R".into(),
            "tickets".into(),
            "daily".into(),
            "{}".into(),
            "[]".into(),
            "{}".into(),
            0,
        );
        use crate::scheduled_reports;
        let report = ctx.db.scheduled_reports().iter().next().unwrap();
        let id = report.id.clone();
        mark_report_error(&ctx, id.clone(), "Connection failed".into());
        let updated = ctx.db.scheduled_reports().id().find(&id).unwrap();
        assert_eq!(updated.last_error, "Connection failed");
    }

    #[test]
    fn test_delete_nonexistent_scheduled_report_doesnt_panic() {
        let ctx = test_ctx();
        delete_scheduled_report(&ctx, "nonexistent".into());
        use crate::scheduled_reports;
        assert_eq!(ctx.db.scheduled_reports().iter().count(), 0);
    }

    // ──────────────────────────────────────────────
    //  INVOICES
    // ──────────────────────────────────────────────

    #[test]
    fn test_create_invoice() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t_inv".into(),
            "cust_1".into(),
            "tkt_1".into(),
            "Test invoice".into(),
            "Net 30".into(),
            2000000,
            "USD".into(),
        );
        use crate::invoices;
        let invoices: Vec<Invoice> = ctx.db.invoices().iter().collect();
        assert_eq!(invoices.len(), 1);
        assert_eq!(invoices[0].status, "draft");
        assert_eq!(invoices[0].currency, "USD");
    }

    #[test]
    fn test_add_invoice_line_item() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t".into(),
            "c".into(),
            "t".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        );
        use crate::invoices;
        let inv = ctx.db.invoices().iter().next().unwrap();
        let inv_id = inv.id.clone();
        add_invoice_line_item(
            &ctx,
            inv_id.clone(),
            "part".into(),
            "Screen repair".into(),
            1.0,
            50.0,
        );
        let items: Vec<InvoiceLineItem> = ctx
            .db
            .invoice_line_items()
            .iter()
            .filter(|i| i.invoice_id == inv_id)
            .collect();
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].description, "Screen repair");
    }

    #[test]
    fn test_delete_invoice_line_item() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t".into(),
            "c".into(),
            "t".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        );
        use crate::invoices;
        let inv = ctx.db.invoices().iter().next().unwrap();
        let inv_id = inv.id.clone();
        add_invoice_line_item(
            &ctx,
            inv_id.clone(),
            "part".into(),
            "Item".into(),
            1.0,
            10.0,
        );
        use crate::invoice_line_items;
        let item = ctx.db.invoice_line_items().iter().next().unwrap();
        let item_id = item.id.clone();
        delete_invoice_line_item(&ctx, item_id);
        assert_eq!(ctx.db.invoice_line_items().iter().count(), 0);
    }

    #[test]
    fn test_update_invoice_status() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t".into(),
            "c".into(),
            "t".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        );
        use crate::invoices;
        let inv = ctx.db.invoices().iter().next().unwrap();
        let id = inv.id.clone();
        update_invoice_status(&ctx, id.clone(), "sent".into());
        let updated = ctx.db.invoices().id().find(&id).unwrap();
        assert_eq!(updated.status, "sent");
    }

    #[test]
    fn test_set_invoice_tax_rate() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t".into(),
            "c".into(),
            "t".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        );
        use crate::invoices;
        let inv = ctx.db.invoices().iter().next().unwrap();
        let id = inv.id.clone();
        set_invoice_tax_rate(&ctx, id.clone(), 8.5);
        let updated = ctx.db.invoices().id().find(&id).unwrap();
        assert_eq!(updated.tax_rate, 8.5);
    }

    #[test]
    fn test_delete_invoice() {
        let ctx = test_ctx();
        create_invoice(
            &ctx,
            "t".into(),
            "c".into(),
            "t".into(),
            "".into(),
            "".into(),
            0,
            "USD".into(),
        );
        use crate::invoices;
        let inv = ctx.db.invoices().iter().next().unwrap();
        let id = inv.id.clone();
        delete_invoice(&ctx, id.clone());
        assert_eq!(ctx.db.invoices().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_invoice_doesnt_panic() {
        let ctx = test_ctx();
        delete_invoice(&ctx, "nonexistent".into());
        use crate::invoices;
        assert_eq!(ctx.db.invoices().iter().count(), 0);
    }

    // ──────────────────────────────────────────────
    //  ESTIMATES
    // ──────────────────────────────────────────────

    #[test]
    fn test_create_estimate() {
        let ctx = test_ctx();
        create_estimate(
            &ctx,
            "t_est".into(),
            "cust_1".into(),
            "tkt_1".into(),
            "Test estimate".into(),
            3000000,
            "USD".into(),
        );
        use crate::estimates;
        let estimates: Vec<Estimate> = ctx.db.estimates().iter().collect();
        assert_eq!(estimates.len(), 1);
        assert_eq!(estimates[0].status, "draft");
    }

    #[test]
    fn test_update_estimate_status() {
        let ctx = test_ctx();
        create_estimate(
            &ctx,
            "t".into(),
            "c".into(),
            "t".into(),
            "".into(),
            0,
            "USD".into(),
        );
        use crate::estimates;
        let est = ctx.db.estimates().iter().next().unwrap();
        let id = est.id.clone();
        update_estimate_status(&ctx, id.clone(), "approved".into());
        let updated = ctx.db.estimates().id().find(&id).unwrap();
        assert_eq!(updated.status, "approved");
    }

    #[test]
    fn test_add_estimate_line_item() {
        let ctx = test_ctx();
        create_estimate(
            &ctx,
            "t".into(),
            "c".into(),
            "t".into(),
            "".into(),
            0,
            "USD".into(),
        );
        use crate::estimates;
        let est = ctx.db.estimates().iter().next().unwrap();
        let est_id = est.id.clone();
        add_estimate_line_item(
            &ctx,
            est_id.clone(),
            "labor".into(),
            "Diagnostic".into(),
            1.0,
            75.0,
        );
        let items: Vec<EstimateLineItem> = ctx
            .db
            .estimate_line_items()
            .iter()
            .filter(|i| i.estimate_id == est_id)
            .collect();
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].description, "Diagnostic");
    }

    #[test]
    fn test_delete_estimate() {
        let ctx = test_ctx();
        create_estimate(
            &ctx,
            "t".into(),
            "c".into(),
            "t".into(),
            "".into(),
            0,
            "USD".into(),
        );
        use crate::estimates;
        let est = ctx.db.estimates().iter().next().unwrap();
        let id = est.id.clone();
        delete_estimate(&ctx, id.clone());
        assert_eq!(ctx.db.estimates().iter().count(), 0);
    }

    // ──────────────────────────────────────────────
    //  BOOKKEEPING SAFETY
    // ──────────────────────────────────────────────

    #[test]
    fn test_mark_overdue_invoices_doesnt_panic() {
        let ctx = test_ctx();
        mark_overdue_invoices(&ctx);
        assert!(true);
    }

    #[test]
    fn test_generate_recurring_invoices_doesnt_panic() {
        let ctx = test_ctx();
        generate_recurring_invoices(&ctx);
        assert!(true);
    }

    #[test]
    fn test_convert_estimate_to_invoice_doesnt_panic_on_nonexistent() {
        let ctx = test_ctx();
        convert_estimate_to_invoice(&ctx, "nonexistent".into());
        assert!(true);
    }
}
