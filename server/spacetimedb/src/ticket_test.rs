use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::ticket::ticket;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_ticket() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t_tkt".into(),
            "cust_1".into(),
            "Broken screen".into(),
            "Customer dropped phone".into(),
            "Phone".into(),
            "iPhone 14".into(),
            "SN12345".into(),
            "high".into(),
        );
        let tickets: Vec<Ticket> = ctx.db.ticket().iter().collect();
        assert_eq!(tickets.len(), 1);
        let t = &tickets[0];
        assert!(t.id.starts_with("tkt_"));
        assert_eq!(t.ticket_number, 1001);
        assert_eq!(t.status, "new");
        assert_eq!(t.priority, "high");
        assert_eq!(t.title, "Broken screen");
        assert_eq!(t.customer_id, "cust_1");
        assert_eq!(t.device_model, "iPhone 14");
        assert_eq!(t.device_serial, "SN12345");
        assert!(t.created_at > 0);
    }

    #[test]
    fn test_create_ticket_increments_number() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "T1".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        create_ticket(
            &ctx,
            "t".into(),
            "c2".into(),
            "T2".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "medium".into(),
        );
        let numbers: Vec<u64> = ctx.db.ticket().iter().map(|t| t.ticket_number).collect();
        assert!(numbers.contains(&1001));
        assert!(numbers.contains(&1002));
    }

    #[test]
    fn test_ticket_defaults() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        let t = ctx.db.ticket().iter().next().unwrap();
        assert_eq!(t.device_imei, "");
        assert_eq!(t.device_password, "");
        assert_eq!(t.assigned_user_id, "");
        assert_eq!(t.notes, "");
        assert_eq!(t.invoice_id, "");
        assert_eq!(t.estimate_id, "");
    }

    #[test]
    fn test_update_ticket_status() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Test".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        let id = ctx.db.ticket().iter().next().unwrap().id.clone();
        assert_eq!(ctx.db.ticket().id().find(&id).unwrap().status, "new");
        update_ticket_status(&ctx, id.clone(), "in_progress".into());
        assert_eq!(
            ctx.db.ticket().id().find(&id).unwrap().status,
            "in_progress"
        );
    }

    #[test]
    fn test_update_nonexistent_ticket() {
        let ctx = test_ctx();
        update_ticket_status(&ctx, "tkt_nonexistent".into(), "closed".into());
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_assign_ticket() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Assign".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        let id = ctx.db.ticket().iter().next().unwrap().id.clone();
        assert_eq!(ctx.db.ticket().id().find(&id).unwrap().assigned_user_id, "");
        assign_ticket(&ctx, id.clone(), "tech_42".into());
        assert_eq!(
            ctx.db.ticket().id().find(&id).unwrap().assigned_user_id,
            "tech_42"
        );
    }

    #[test]
    fn test_assign_nonexistent_ticket() {
        let ctx = test_ctx();
        assign_ticket(&ctx, "tkt_nonexistent".into(), "user_x".into());
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_add_ticket_note() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Note".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        let ticket_id = ctx.db.ticket().iter().next().unwrap().id.clone();
        add_ticket_note(
            &ctx,
            ticket_id.clone(),
            "tech_1".into(),
            "Customer called back".into(),
            false,
        );
        let notes: Vec<TicketNote> = ctx.db.ticket_note().iter().collect();
        assert_eq!(notes.len(), 1);
        assert!(notes[0].id.starts_with("tnote_"));
        assert_eq!(notes[0].ticket_id, ticket_id);
        assert_eq!(notes[0].author, "tech_1");
        assert_eq!(notes[0].content, "Customer called back");
        assert!(!notes[0].internal);
    }

    #[test]
    fn test_add_internal_ticket_note() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "IntNote".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        let ticket_id = ctx.db.ticket().iter().next().unwrap().id.clone();
        add_ticket_note(
            &ctx,
            ticket_id,
            "tech_1".into(),
            "Internal note".into(),
            true,
        );
        let note = ctx.db.ticket_note().iter().next().unwrap();
        assert!(note.internal);
    }

    #[test]
    fn test_delete_ticket() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Del".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        assert_eq!(ctx.db.ticket().iter().count(), 1);
        let id = ctx.db.ticket().iter().next().unwrap().id.clone();
        delete_ticket(&ctx, id);
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_ticket() {
        let ctx = test_ctx();
        delete_ticket(&ctx, "tkt_nonexistent".into());
        assert_eq!(ctx.db.ticket().iter().count(), 0);
    }

    #[test]
    fn test_start_ticket_timer() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Timer".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "high".into(),
        );
        let ticket_id = ctx.db.ticket().iter().next().unwrap().id.clone();
        start_ticket_timer(&ctx, ticket_id, "user_1".into());
        let timers: Vec<TicketTimer> = ctx.db.ticket_timer().iter().collect();
        assert_eq!(timers.len(), 1);
        assert!(timers[0].id.starts_with("tmr_"));
        assert!(timers[0].running);
    }

    #[test]
    fn test_stop_ticket_timer() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Stop".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "high".into(),
        );
        let ticket_id = ctx.db.ticket().iter().next().unwrap().id.clone();
        start_ticket_timer(&ctx, ticket_id, "user_1".into());
        let timer_id = ctx.db.ticket_timer().iter().next().unwrap().id.clone();
        stop_ticket_timer(&ctx, timer_id.clone());
        let stopped = ctx.db.ticket_timer().id().find(&timer_id).unwrap();
        assert!(!stopped.running);
        assert!(stopped.end_time > 0);
    }

    #[test]
    fn test_stop_nonexistent_timer() {
        let ctx = test_ctx();
        stop_ticket_timer(&ctx, "tmr_nonexistent".into());
        assert_eq!(ctx.db.ticket_timer().iter().count(), 0);
    }

    #[test]
    fn test_start_timer_stops_previous() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "Multi".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "medium".into(),
        );
        let ticket_id = ctx.db.ticket().iter().next().unwrap().id.clone();
        start_ticket_timer(&ctx, ticket_id.clone(), "user_1".into());
        assert_eq!(
            ctx.db
                .ticket_timer()
                .iter()
                .filter(|t: &TicketTimer| t.running)
                .count(),
            1
        );
        start_ticket_timer(&ctx, ticket_id, "user_1".into());
        let running: Vec<TicketTimer> =
            ctx.db.ticket_timer().iter().filter(|t| t.running).collect();
        assert_eq!(running.len(), 1);
        assert_eq!(ctx.db.ticket_timer().iter().count(), 2);
    }

    #[test]
    fn test_delete_ticket_timer() {
        let ctx = test_ctx();
        create_ticket(
            &ctx,
            "t".into(),
            "c1".into(),
            "DelTmr".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "low".into(),
        );
        let ticket_id = ctx.db.ticket().iter().next().unwrap().id.clone();
        start_ticket_timer(&ctx, ticket_id, "user_1".into());
        assert_eq!(ctx.db.ticket_timer().iter().count(), 1);
        let timer_id = ctx.db.ticket_timer().iter().next().unwrap().id.clone();
        delete_ticket_timer(&ctx, timer_id);
        assert_eq!(ctx.db.ticket_timer().iter().count(), 0);
    }
}
