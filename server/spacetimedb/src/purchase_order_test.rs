use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::purchase_order::purchase_order;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_purchase_order() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t_po".into(),
            "Acme Corp".into(),
            "Rush order".into(),
            "USD".into(),
        );
        let pos: Vec<PurchaseOrder> = ctx.db.purchase_order().iter().collect();
        assert_eq!(pos.len(), 1);
        let po = &pos[0];
        assert!(po.id.starts_with("po_"));
        assert_eq!(po.vendor_name, "Acme Corp");
        assert_eq!(po.status, "draft");
        assert_eq!(po.po_number, 1001);
        assert_eq!(po.notes, "Rush order");
        assert_eq!(po.currency, "USD");
        assert_eq!(po.subtotal, 0.0);
        assert!(po.created_at > 0);
        assert_eq!(po.created_at, po.updated_at);
    }

    #[test]
    fn test_create_purchase_order_increments_po_number() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_1".into(), "V1".into(), "".into(), "USD".into());
        create_purchase_order(&ctx, "t_1".into(), "V2".into(), "".into(), "USD".into());
        let numbers: Vec<u64> = ctx
            .db
            .purchase_order()
            .iter()
            .map(|po| po.po_number)
            .collect();
        assert!(numbers.contains(&1001));
        assert!(numbers.contains(&1002));
    }

    #[test]
    fn test_add_po_line_item() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(
            &ctx,
            po_id.clone(),
            "p_1".into(),
            "Widget".into(),
            2.0,
            25.0,
        );
        let items: Vec<PurchaseOrderLineItem> = ctx.db.purchase_order_line_item().iter().collect();
        assert_eq!(items.len(), 1);
        let item = &items[0];
        assert!(item.id.starts_with("poli_"));
        assert_eq!(item.description, "Widget");
        assert_eq!(item.product_id, "p_1");
        assert!((item.total - 50.0).abs() < 0.001);
    }

    #[test]
    fn test_add_po_line_item_recalculates_totals() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(&ctx, po_id.clone(), "".into(), "Item1".into(), 3.0, 10.0);
        add_po_line_item(&ctx, po_id.clone(), "".into(), "Item2".into(), 2.0, 20.0);
        let po = ctx
            .db
            .purchase_order()
            .id()
            .find(&po_id)
            .expect("PO exists");
        assert!((po.subtotal - 70.0).abs() < 0.001);
        assert!((po.total - 70.0).abs() < 0.001);
    }

    #[test]
    fn test_delete_po_line_item() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(&ctx, po_id.clone(), "".into(), "Item1".into(), 1.0, 10.0);
        add_po_line_item(&ctx, po_id.clone(), "".into(), "Item2".into(), 1.0, 20.0);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 2);
        let item_id = ctx
            .db
            .purchase_order_line_item()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        delete_po_line_item(&ctx, po_id.clone(), item_id);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 1);
    }

    #[test]
    fn test_update_po_status() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        assert_eq!(
            ctx.db.purchase_order().id().find(&po_id).unwrap().status,
            "draft"
        );
        update_po_status(&ctx, po_id.clone(), "cancelled".into());
        assert_eq!(
            ctx.db.purchase_order().id().find(&po_id).unwrap().status,
            "cancelled"
        );
    }

    #[test]
    fn test_submit_for_approval() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        submit_for_approval(&ctx, po_id.clone());
        assert_eq!(
            ctx.db.purchase_order().id().find(&po_id).unwrap().status,
            "pending_approval"
        );
    }

    #[test]
    fn test_submit_already_non_draft_noop() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        submit_for_approval(&ctx, po_id.clone());
        // Second submit on non-draft should be noop
        submit_for_approval(&ctx, po_id.clone());
        assert_eq!(
            ctx.db.purchase_order().id().find(&po_id).unwrap().status,
            "pending_approval"
        );
    }

    #[test]
    fn test_approve_po() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        submit_for_approval(&ctx, po_id.clone());
        approve_po(&ctx, po_id.clone(), "admin_1".into());
        let po = ctx.db.purchase_order().id().find(&po_id).unwrap();
        assert_eq!(po.status, "approved");
        assert_eq!(po.approved_by, "admin_1");
        assert!(po.approved_at > 0);
    }

    #[test]
    fn test_approve_non_pending_po_noop() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        // Can't approve a draft directly
        approve_po(&ctx, po_id.clone(), "user_x".into());
        assert_eq!(
            ctx.db.purchase_order().id().find(&po_id).unwrap().status,
            "draft"
        );
    }

    #[test]
    fn test_reject_po() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        submit_for_approval(&ctx, po_id.clone());
        reject_po(&ctx, po_id.clone());
        assert_eq!(
            ctx.db.purchase_order().id().find(&po_id).unwrap().status,
            "draft"
        );
    }

    #[test]
    fn test_reject_draft_po_noop() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        // Rejecting a draft should be noop
        reject_po(&ctx, po_id.clone());
        assert_eq!(
            ctx.db.purchase_order().id().find(&po_id).unwrap().status,
            "draft"
        );
    }

    #[test]
    fn test_receive_po_item() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(&ctx, po_id.clone(), "".into(), "Item".into(), 10.0, 5.0);
        let li_id = ctx
            .db
            .purchase_order_line_item()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        receive_po_item(&ctx, li_id.clone(), 5.0);
        let item = ctx
            .db
            .purchase_order_line_item()
            .id()
            .find(&li_id)
            .expect("line item exists");
        assert_eq!(item.received_quantity, 5.0);
        // PO status becomes "partial"
        let po = ctx.db.purchase_order().id().find(&po_id).unwrap();
        assert_eq!(po.status, "partial");
    }

    #[test]
    fn test_receive_po_item_full_received() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(&ctx, po_id.clone(), "".into(), "Item".into(), 10.0, 5.0);
        let li_id = ctx
            .db
            .purchase_order_line_item()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        receive_po_item(&ctx, li_id.clone(), 10.0);
        let po = ctx.db.purchase_order().id().find(&po_id).unwrap();
        assert_eq!(po.status, "received");
    }

    #[test]
    fn test_receive_excess_quantity() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(&ctx, po_id.clone(), "".into(), "Item".into(), 10.0, 5.0);
        let li_id = ctx
            .db
            .purchase_order_line_item()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        receive_po_item(&ctx, li_id.clone(), 15.0);
        let item = ctx
            .db
            .purchase_order_line_item()
            .id()
            .find(&li_id)
            .expect("line item exists");
        assert_eq!(item.received_quantity, 15.0);
    }

    #[test]
    fn test_delete_purchase_order_cascades_items() {
        let ctx = test_ctx();
        create_purchase_order(&ctx, "t_po".into(), "V".into(), "".into(), "USD".into());
        let po_id = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(&ctx, po_id.clone(), "".into(), "Item".into(), 1.0, 10.0);
        assert_eq!(ctx.db.purchase_order().iter().count(), 1);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 1);
        delete_purchase_order(&ctx, po_id);
        assert_eq!(ctx.db.purchase_order().iter().count(), 0);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_purchase_order() {
        let ctx = test_ctx();
        delete_purchase_order(&ctx, "po_nonexistent".into());
        assert_eq!(ctx.db.purchase_order().iter().count(), 0);
    }

    #[test]
    fn test_update_nonexistent_po_noop() {
        let ctx = test_ctx();
        update_po_status(&ctx, "po_nonexistent".into(), "approved".into());
        assert_eq!(ctx.db.purchase_order().iter().count(), 0);
    }

    #[test]
    fn test_add_line_item_to_nonexistent_po() {
        let ctx = test_ctx();
        add_po_line_item(
            &ctx,
            "po_nonexistent".into(),
            "".into(),
            "Ghost".into(),
            1.0,
            1.0,
        );
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 1);
    }
}
