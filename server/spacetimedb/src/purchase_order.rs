// TODO (kanban): Replace 30 unwrap() call(s) with proper error handling
use crate::inventory::inventory_adjustment;
use crate::product::products;
use spacetimedb::*;

#[spacetimedb::table(accessor = purchase_order, public)]
#[derive(Debug, Clone)]
pub struct PurchaseOrder {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub vendor_name: String,
    pub po_number: u64,
    pub status: String, // draft → pending_approval → approved → sent → partial → received → cancelled
    pub subtotal: f64,
    pub tax_amount: f64,
    pub shipping_cost: f64,
    pub total: f64,
    pub notes: String,
    pub created_at: u64,
    pub updated_at: u64,
    pub approved_by: String,
    pub currency: String,
    #[default(0u64)]
    pub approved_at: u64,
}

#[spacetimedb::table(accessor = purchase_order_line_item, public)]
#[derive(Debug, Clone)]
pub struct PurchaseOrderLineItem {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub purchase_order_id: String,
    pub product_id: String,
    pub description: String,
    pub quantity: f64,
    pub unit_price: f64,
    pub total: f64,
    pub received_quantity: f64,
}

#[spacetimedb::reducer]
pub fn create_purchase_order(
    ctx: &ReducerContext,
    tenant_id: String,
    vendor_name: String,
    notes: String,
    currency: String,
    shipping_cost: f64,
) {
    let id = super::make_id("po", ctx);
    let now = super::now_ms(ctx);
    let po_number = ctx.db.purchase_order().iter().count() as u64 + 1001;
    ctx.db.purchase_order().insert(PurchaseOrder {
        id,
        tenant_id,
        vendor_name,
        po_number,
        status: "draft".to_string(),
        subtotal: 0.0,
        tax_amount: 0.0,
        shipping_cost,
        total: 0.0,
        notes,
        created_at: now,
        updated_at: now,
        approved_by: String::new(),
        currency,
        approved_at: 0,
    });
}

fn recalc_po(ctx: &ReducerContext, po_id: &str) {
    let now = super::now_ms(ctx);
    let mut subtotal = 0.0_f64;
    let mut total_received = 0.0_f64;
    let mut total_qty = 0.0_f64;
    for item in ctx
        .db
        .purchase_order_line_item()
        .iter()
        .filter(|i| i.purchase_order_id == po_id)
    {
        subtotal += item.total;
        total_received += item.received_quantity;
        total_qty += item.quantity;
    }
    if let Some(mut po) = ctx.db.purchase_order().id().find(po_id.to_string()) {
        po.subtotal = subtotal;
        po.total = subtotal + po.tax_amount + po.shipping_cost;
        po.updated_at = now;
        // Auto-update status based on received quantities
        if total_qty > 0.0 && total_received >= total_qty {
            po.status = "received".to_string();
        } else if total_received > 0.0 {
            po.status = "partial".to_string();
        }
        ctx.db.purchase_order().id().update(po);
    }
}

#[spacetimedb::reducer]
pub fn add_po_line_item(
    ctx: &ReducerContext,
    purchase_order_id: String,
    product_id: String,
    description: String,
    quantity: f64,
    unit_price: f64,
) {
    let id = super::make_id("poli", ctx);
    let total = quantity * unit_price;
    // Derive tenant_id from the parent PO
    let tenant_id = ctx
        .db
        .purchase_order()
        .id()
        .find(&purchase_order_id)
        .map_or(String::new(), |po| po.tenant_id.clone());
    ctx.db
        .purchase_order_line_item()
        .insert(PurchaseOrderLineItem {
            id,
            tenant_id,
            purchase_order_id: purchase_order_id.clone(),
            product_id,
            description,
            quantity,
            unit_price,
            total,
            received_quantity: 0.0,
        });
    recalc_po(ctx, &purchase_order_id);
}

#[spacetimedb::reducer]
pub fn delete_po_line_item(ctx: &ReducerContext, po_id: String, item_id: String) {
    ctx.db.purchase_order_line_item().id().delete(&item_id);
    recalc_po(ctx, &po_id);
}

#[spacetimedb::reducer]
pub fn update_po_status(ctx: &ReducerContext, id: String, status: String) {
    if let Some(mut po) = ctx.db.purchase_order().id().find(&id) {
        po.status = status;
        po.updated_at = super::now_ms(ctx);
        ctx.db.purchase_order().id().update(po);
    }
}

#[spacetimedb::reducer]
pub fn submit_for_approval(ctx: &ReducerContext, id: String) {
    if let Some(mut po) = ctx.db.purchase_order().id().find(&id) {
        if po.status != "draft" {
            return;
        }
        po.status = "pending_approval".to_string();
        po.updated_at = super::now_ms(ctx);
        ctx.db.purchase_order().id().update(po);
    }
}

#[spacetimedb::reducer]
pub fn approve_po(ctx: &ReducerContext, id: String, user_id: String) {
    if let Some(mut po) = ctx.db.purchase_order().id().find(&id) {
        if po.status != "pending_approval" {
            return;
        }
        po.status = "approved".to_string();
        po.approved_by = user_id;
        po.approved_at = super::now_ms(ctx);
        po.updated_at = super::now_ms(ctx);
        ctx.db.purchase_order().id().update(po);
    }
}

#[spacetimedb::reducer]
pub fn reject_po(ctx: &ReducerContext, id: String) {
    if let Some(mut po) = ctx.db.purchase_order().id().find(&id) {
        if po.status != "pending_approval" {
            return;
        }
        po.status = "draft".to_string();
        po.updated_at = super::now_ms(ctx);
        ctx.db.purchase_order().id().update(po);
    }
}

#[spacetimedb::reducer]
pub fn receive_po_item(ctx: &ReducerContext, id: String, received_quantity: f64) {
    if let Some(item) = ctx.db.purchase_order_line_item().id().find(&id) {
        ctx.db
            .purchase_order_line_item()
            .id()
            .update(PurchaseOrderLineItem {
                received_quantity,
                ..item.clone()
            });
        recalc_po(ctx, &item.purchase_order_id);

        // Update product stock and create inventory adjustment
        if !item.product_id.is_empty() {
            let qty_change = received_quantity - item.received_quantity;
            if (qty_change - 0.0).abs() > f64::EPSILON {
                if let Some(mut p) = ctx.db.products().id().find(&item.product_id) {
                    p.quantity_on_hand += qty_change;
                    p.quantity_available = p.quantity_on_hand - p.quantity_committed;
                    p.updated_at = super::now_ms(ctx);
                    ctx.db.products().id().update(p);
                }
                let po_id = item.purchase_order_id.clone();
                let po_tenant_id = ctx
                    .db
                    .purchase_order()
                    .id()
                    .find(&po_id)
                    .map_or(String::new(), |po| po.tenant_id.clone());
                // Create inventory adjustment record using PO's tenant_id
                let adj_id = super::make_id("adj", ctx);
                ctx.db
                    .inventory_adjustment()
                    .insert(super::InventoryAdjustment {
                        id: adj_id,
                        tenant_id: po_tenant_id,
                        product_id: item.product_id.clone(),
                        quantity_change: qty_change,
                        reason: "received".to_string(),
                        reference_id: id.clone(),
                        notes: format!("PO receiving, line item: {}", item.description),
                        user_id: String::new(),
                        created_at: super::now_ms(ctx),
                    });
            }
        }
    }
}

#[spacetimedb::reducer]
pub fn delete_purchase_order(ctx: &ReducerContext, id: String) {
    // Remove all line items first
    let items: Vec<PurchaseOrderLineItem> = ctx
        .db
        .purchase_order_line_item()
        .iter()
        .filter(|i| i.purchase_order_id == id)
        .collect();
    for item in items {
        ctx.db.purchase_order_line_item().id().delete(&item.id);
    }
    ctx.db.purchase_order().id().delete(&id);
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_purchase_order() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t_po".into(),
            "Vendor Co".into(),
            "Urgent".into(),
            "USD".into(),
            0.0,
        );
        let pos: Vec<PurchaseOrder> = ctx.db.purchase_order().iter().collect();
        assert_eq!(pos.len(), 1);
        let po = &pos[0];
        assert!(po.id.starts_with("po_"));
        assert_eq!(po.vendor_name, "Vendor Co");
        assert_eq!(po.status, "draft");
        assert_eq!(po.currency, "USD");
        assert!(po.po_number > 0);
        assert_eq!(po.shipping_cost, 0.0);
        assert!(po.created_at > 0);
        assert_eq!(po.created_at, po.updated_at);
    }

    #[test]
    fn test_create_purchase_order_with_shipping() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            "notes".into(),
            "EUR".into(),
            15.50,
        );
        let po = ctx.db.purchase_order().iter().next().unwrap();
        assert_eq!(po.notes, "notes");
        assert_eq!(po.shipping_cost, 15.50);
        assert_eq!(po.currency, "EUR");
    }

    #[test]
    fn test_add_po_line_item() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(
            &ctx,
            poid.clone(),
            "prod_1".into(),
            "Cable".into(),
            10.0,
            5.0,
        );
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 1);
        let item = ctx.db.purchase_order_line_item().iter().next().unwrap();
        assert_eq!(item.description, "Cable");
        assert_eq!(item.quantity, 10.0);
        assert_eq!(item.unit_price, 5.0);
        assert!((item.total - 50.0).abs() < 0.01);
        // PO subtotal should be recalculated
        let po = ctx.db.purchase_order().id().find(&poid).unwrap();
        assert!((po.subtotal - 50.0).abs() < 0.01);
        assert!((po.total - 50.0).abs() < 0.01);
    }

    #[test]
    fn test_delete_po_line_item() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(&ctx, poid.clone(), "p1".into(), "A".into(), 2.0, 10.0);
        add_po_line_item(&ctx, poid.clone(), "p2".into(), "B".into(), 1.0, 20.0);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 2);
        let item_id = ctx
            .db
            .purchase_order_line_item()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        delete_po_line_item(&ctx, poid.clone(), item_id);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 1);
        let po = ctx.db.purchase_order().id().find(&poid).unwrap();
        assert!((po.subtotal - 20.0).abs() < 0.01);
    }

    #[test]
    fn test_update_po_status() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        assert_eq!(
            ctx.db.purchase_order().id().find(&poid).unwrap().status,
            "draft"
        );
        update_po_status(&ctx, poid.clone(), "sent".into());
        assert_eq!(
            ctx.db.purchase_order().id().find(&poid).unwrap().status,
            "sent"
        );
    }

    #[test]
    fn test_po_submit_for_approval() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        assert_eq!(
            ctx.db.purchase_order().id().find(&poid).unwrap().status,
            "draft"
        );
        submit_for_approval(&ctx, poid.clone());
        assert_eq!(
            ctx.db.purchase_order().id().find(&poid).unwrap().status,
            "pending_approval"
        );
    }

    #[test]
    fn test_po_submit_from_non_draft_is_noop() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        update_po_status(&ctx, poid.clone(), "sent".into());
        submit_for_approval(&ctx, poid);
        // Should stay sent, not change to pending_approval
        assert_eq!(
            ctx.db.purchase_order().iter().next().unwrap().status,
            "sent"
        );
    }

    #[test]
    fn test_po_approve() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
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
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        approve_po(&ctx, poid, "admin".into());
        assert_eq!(
            ctx.db.purchase_order().iter().next().unwrap().status,
            "draft"
        );
    }

    #[test]
    fn test_po_reject() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        submit_for_approval(&ctx, poid.clone());
        reject_po(&ctx, poid.clone());
        assert_eq!(
            ctx.db.purchase_order().id().find(&poid).unwrap().status,
            "draft"
        );
    }

    #[test]
    fn test_po_reject_from_draft_is_noop() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        reject_po(&ctx, poid);
        assert_eq!(
            ctx.db.purchase_order().iter().next().unwrap().status,
            "draft"
        );
    }

    #[test]
    fn test_po_receive_item() {
        let ctx = test_ctx();
        // Create product
        ctx.db.products().insert(crate::Product {
            id: "prod_rcv_test".into(),
            tenant_id: "t_rcv".into(),
            name: "RAM".into(),
            sku: "RAM-8GB".into(),
            barcode: String::new(),
            description: String::new(),
            category: "Parts".into(),
            price: 49.99,
            cost: 25.0,
            quantity_on_hand: 5.0,
            quantity_committed: 0.0,
            quantity_available: 5.0,
            min_stock: 2.0,
            location: "C3".into(),
            active: true,
            created_at: 0,
            updated_at: 0,
        });
        let pid = ctx.db.products().iter().next().unwrap().id.clone();
        create_purchase_order(
            &ctx,
            "t_rcv".into(),
            "Sup".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(
            &ctx,
            poid.clone(),
            pid.clone(),
            "8GB DDR4".into(),
            10.0,
            30.0,
        );
        let item_id = ctx
            .db
            .purchase_order_line_item()
            .iter()
            .next()
            .unwrap()
            .id
            .clone();
        assert_eq!(
            ctx.db
                .purchase_order_line_item()
                .id()
                .find(&item_id)
                .unwrap()
                .received_quantity,
            0.0
        );
        receive_po_item(&ctx, item_id.clone(), 5.0);
        assert_eq!(
            ctx.db
                .purchase_order_line_item()
                .id()
                .find(&item_id)
                .unwrap()
                .received_quantity,
            5.0
        );
        // Product stock should increase
        assert_eq!(
            ctx.db.products().id().find(&pid).unwrap().quantity_on_hand,
            10.0
        );
        // Inventory adjustment should exist
        assert_eq!(ctx.db.inventory_adjustment().iter().count(), 1);
    }

    #[test]
    fn test_delete_purchase_order() {
        let ctx = test_ctx();
        create_purchase_order(
            &ctx,
            "t".into(),
            "V".into(),
            String::new(),
            "USD".into(),
            0.0,
        );
        let poid = ctx.db.purchase_order().iter().next().unwrap().id.clone();
        add_po_line_item(&ctx, poid.clone(), "p1".into(), "A".into(), 2.0, 10.0);
        add_po_line_item(&ctx, poid.clone(), "p2".into(), "B".into(), 1.0, 20.0);
        assert_eq!(ctx.db.purchase_order().iter().count(), 1);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 2);
        delete_purchase_order(&ctx, poid);
        assert_eq!(ctx.db.purchase_order().iter().count(), 0);
        assert_eq!(ctx.db.purchase_order_line_item().iter().count(), 0);
    }

    #[test]
    fn test_po_nonexistent_operations() {
        let ctx = test_ctx();
        update_po_status(&ctx, "po_nope".into(), "sent".into());
        submit_for_approval(&ctx, "po_nope".into());
        approve_po(&ctx, "po_nope".into(), "u".into());
        reject_po(&ctx, "po_nope".into());
        receive_po_item(&ctx, "poli_nope".into(), 0.0);
        delete_purchase_order(&ctx, "po_nope".into());
        assert_eq!(ctx.db.purchase_order().iter().count(), 0);
    }
}
