use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::recurring_invoice_rule::recurring_invoice_rules;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_recurring_invoice_rule() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(
            &ctx,
            "t_rir".into(),
            "cust_1".into(),
            "Monthly Rent".into(),
            "monthly".into(),
            1,
            15,
            r#"[{"description":"Rent","quantity":1,"unit_price":1000}]"#.into(),
            1700000000000,
        );
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
        create_recurring_invoice_rule(
            &ctx,
            "t".into(),
            "c1".into(),
            "Old".into(),
            "monthly".into(),
            1,
            15,
            "[]".into(),
            1000,
        );
        let id = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .next()
            .expect("expected at least one recurring_invoice_rules record")
            .id
            .clone();
        update_recurring_invoice_rule(
            &ctx,
            id.clone(),
            "New Name".into(),
            "weekly".into(),
            2,
            30,
            r#"[{"desc":"X"}]"#.into(),
            2000,
            "paused".into(),
        );
        let updated = ctx
            .db
            .recurring_invoice_rules()
            .id()
            .find(&id)
            .expect("expected record to exist");
        assert_eq!(updated.name, "New Name");
        assert_eq!(updated.frequency, "weekly");
        assert_eq!(updated.status, "paused");
    }

    #[test]
    fn test_delete_recurring_invoice_rule() {
        let ctx = test_ctx();
        create_recurring_invoice_rule(
            &ctx,
            "t".into(),
            "c1".into(),
            "Del".into(),
            "m".into(),
            1,
            15,
            "[]".into(),
            1000,
        );
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 1);
        let id = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .next()
            .expect("expected at least one recurring_invoice_rules record")
            .id
            .clone();
        delete_recurring_invoice_rule(&ctx, id);
        assert_eq!(ctx.db.recurring_invoice_rules().iter().count(), 0);
    }

    #[test]
    fn test_generate_recurring_invoices() {
        let ctx = test_ctx();
        // Create a recurring rule with past-due next_generation_date
        let now = ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000;
        let items = r#"[{"description":"Monthly rent","quantity":1,"unit_price":500}]"#;
        create_recurring_invoice_rule(
            &ctx,
            "t_gr".into(),
            "cust_1".into(),
            "Monthly Rent".into(),
            "monthly".into(),
            1,
            15,
            items.into(),
            now - 1000,
        ); // due now
           // Generate invoices
        assert_eq!(ctx.db.invoices().iter().count(), 0);
        generate_recurring_invoices(&ctx);
        // Should have created 1 invoice
        assert_eq!(ctx.db.invoices().iter().count(), 1);
        let inv = ctx
            .db
            .invoices()
            .iter()
            .next()
            .expect("expected at least one invoices record");
        assert_eq!(inv.tenant_id, "t_gr");
        assert_eq!(inv.customer_id, "cust_1");
        assert!(inv.notes.contains("Monthly Rent"));
        // Line items should be copied
        assert_eq!(ctx.db.invoice_line_items().iter().count(), 1);
        let li = ctx
            .db
            .invoice_line_items()
            .iter()
            .next()
            .expect("expected at least one invoice_line_items record");
        assert_eq!(li.description, "Monthly rent");
        assert!((li.total - 500.0).abs() < 0.01);
        // Rule's next_generation_date should be updated
        let rule = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .next()
            .expect("expected at least one recurring_invoice_rules record");
        assert!(rule.next_generation_date > now - 1000);
        assert_eq!(rule.last_generated_date, now);
    }

    #[test]
    fn test_generate_recurring_no_due_rules() {
        let ctx = test_ctx();
        // Create a rule with future date
        let far_future = 9999999999999999;
        create_recurring_invoice_rule(
            &ctx,
            "t".into(),
            "c1".into(),
            "Future".into(),
            "monthly".into(),
            1,
            15,
            "[]".into(),
            far_future,
        );
        generate_recurring_invoices(&ctx);
        assert_eq!(ctx.db.invoices().iter().count(), 0);
    }

    #[test]
    fn test_generate_recurring_paused_rule_skipped() {
        let ctx = test_ctx();
        let now = ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000;
        create_recurring_invoice_rule(
            &ctx,
            "t".into(),
            "c1".into(),
            "Paused".into(),
            "monthly".into(),
            1,
            15,
            "[]".into(),
            now - 1000,
        );
        // Pause it
        let id = ctx
            .db
            .recurring_invoice_rules()
            .iter()
            .next()
            .expect("expected at least one recurring_invoice_rules record")
            .id
            .clone();
        update_recurring_invoice_rule(
            &ctx,
            id,
            "Paused".into(),
            "monthly".into(),
            1,
            15,
            "[]".into(),
            now - 1000,
            "paused".into(),
        );
        generate_recurring_invoices(&ctx);
        assert_eq!(ctx.db.invoices().iter().count(), 0);
    }

    #[test]
    fn test_generate_recurring_empty_customer_skipped() {
        let ctx = test_ctx();
        let now = ctx.timestamp.to_micros_since_unix_epoch() as u64 / 1000;
        // Rule with empty customer_id
        create_recurring_invoice_rule(
            &ctx,
            "t".into(),
            "".into(),
            "NoCust".into(),
            "monthly".into(),
            1,
            15,
            "[]".into(),
            now - 1000,
        );
        generate_recurring_invoices(&ctx);
        assert_eq!(ctx.db.invoices().iter().count(), 0);
    }
}
