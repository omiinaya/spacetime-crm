//! Integration-style unit tests for STDB reducers.
//!
//! Each test creates isolated dummy ReducerContexts, runs reducers,
//! and asserts table state. Follows the customer_test pattern.

#[cfg(test)]
mod tests {
    use crate::*;
    // Import accessor traits for STDB table access
    use crate::purchase_order::purchase_order;
    use crate::product::products;

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
            "tenant_t".into(), "cust_1".into(), "Broken screen".into(),
            "Cracked glass".into(), "iPhone".into(), "15".into(),
            "SN001".into(), "high".into(),
            "".into(), "".into(),
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
        create_ticket(&ctx, "t".into(), "c1".into(), "Fix".into(), "".into(), "".into(), "".into(), "".into(), "low".into(), "".into(), "".into());
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
        create_ticket(&ctx, "t".into(), "c1".into(), "Assign test".into(), "".into(), "".into(), "".into(), "".into(), "medium".into(), "".into(), "".into());
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
        create_ticket(&ctx, "t".into(), "c1".into(), "Note test".into(), "".into(), "".into(), "".into(), "".into(), "low".into(), "".into(), "".into());
        use crate::ticket::ticket;
        let t = ctx.db.ticket().iter().next().unwrap();
        let tid = t.id.clone();
        add_ticket_note(&ctx, tid.clone(), "Bob".into(), "Checked device".into(), false);
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
        create_ticket(&ctx, "t".into(), "c1".into(), "Delete me".into(), "".into(), "".into(), "".into(), "".into(), "low".into(), "".into(), "".into());
        use crate::ticket::ticket;
        assert_eq!(ctx.db.ticket().iter().count(), 1);
        let id = ctx.db.ticket().iter().next().unwrap().id.clone();
        delete_ticket(&ctx, id);
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_ticket_timer_lifecycle() {
        let ctx = test_ctx();
        create_ticket(&ctx, "t".into(), "c1".into(), "Timer test".into(), "".into(), "".into(), "".into(), "".into(), "low".into(), "".into(), "".into());
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
        record_payment(&ctx, "tenant_p".into(), "inv_1".into(), "cust_1".into(), 150.00, "cash".into(), "REF-001".into(), "Walk-in payment".into(), "USD".into());
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
        record_payment(&ctx, "t".into(), "i".into(), "c".into(), 50.0, "cash".into(), "".into(), "".into(), "USD".into());
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
        create_product(&ctx, "tenant_pr".into(), "Screen".into(), "SCR-001".into(), "".into(), "".into(), "Parts".into(), 29.99, 12.50, 50.0, 5.0, "Aisle-3".into());
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
        create_product(&ctx, "t".into(), "Old".into(), "OLD-001".into(), "".into(), "".into(), "".into(), 10.0, 5.0, 10.0, 0.0, "".into());
        let p = ctx.db.products().iter().next().unwrap();
        let pid = p.id.clone();
        update_product(&ctx, pid.clone(), "New Name".into(), "NEW-001".into(), "".into(), "desc".into(), "cat".into(), 25.0, 8.0, 5.0, "B-12".into());
        let updated = ctx.db.products().id().find(&pid).unwrap();
        assert_eq!(updated.name, "New Name");
    }

    #[test]
    fn test_delete_product() {
        let ctx = test_ctx();
        create_product(&ctx, "t".into(), "Del".into(), "DEL".into(), "".into(), "".into(), "".into(), 1.0, 0.5, 5.0, 0.0, "".into());
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
        create_purchase_order(&ctx, "tenant_po".into(), "vendor_1".into(), "notes".into(), "USD".into(), 0.0);
        let pos: Vec<PurchaseOrder> = ctx.db.purchase_order().iter().collect();
        assert_eq!(pos.len(), 1);
        let po = &pos[0];
        assert_eq!(po.vendor_name, "vendor_1");
        assert_eq!(po.status, "draft");
    }

    #[test]
    fn test_update_po_status() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t".into(), "v1".into(), "".into(), "USD".into(), 0.0);
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
        create_ticket(&ctx, "t_a".into(), "c1".into(), "Tkt A".into(), "".into(), "".into(), "".into(), "".into(), "low".into(), "".into(), "".into());
        create_ticket(&ctx, "t_b".into(), "c2".into(), "Tkt B".into(), "".into(), "".into(), "".into(), "".into(), "high".into(), "".into(), "".into());
        use crate::ticket::ticket;
        let tickets: Vec<Ticket> = ctx.db.ticket().iter().filter(|t| t.tenant_id == "t_a").collect();
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
        create_ticket(&ctx, "t_derived".into(), "c1".into(), "Derive test".into(), "".into(), "".into(), "".into(), "".into(), "low".into(), "".into(), "".into());
        use crate::ticket::ticket;
        let t = ctx.db.ticket().iter().next().unwrap();
        let tid = t.id.clone();
        add_ticket_note(&ctx, tid.clone(), "Tech".into(), "Noted".into(), false);
        use crate::ticket::ticket_note;
        let note = ctx.db.ticket_note().iter().next().unwrap();
        assert_eq!(note.tenant_id, "t_derived");
    }
}
