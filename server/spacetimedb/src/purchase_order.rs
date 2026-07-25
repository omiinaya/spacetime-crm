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
        shipping_cost: 0.0,
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
