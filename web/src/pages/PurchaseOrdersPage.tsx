import { useState, useEffect } from "react";
import { api, PurchaseOrder, PurchaseOrderLineItem } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { ShoppingCart, Plus, Trash2, SendHorizontal, PackageCheck, X, ChevronDown, ChevronUp, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

const statusColors: Record<string, "outline" | "default" | "success" | "destructive"> = {
  draft: "outline",
  sent: "default",
  partial: "default",
  received: "success",
  cancelled: "destructive",
};

export default function PurchaseOrdersPage() {
  const [pos, setPos] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ vendor_name: "", notes: "" });
  const [selectedPo, setSelectedPo] = useState<string | null>(null);
  const [poDetail, setPoDetail] = useState<PurchaseOrder | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [newItemForm, setNewItemForm] = useState({ product_id: "", description: "", quantity: 1, unit_price: 0 });
  const [receiveMode, setReceiveMode] = useState<string | null>(null);
  const [receiveQuantities, setReceiveQuantities] = useState<Record<string, number>>({});

  const load = async () => {
    try {
      const res = await api.purchaseOrders.list();
      setPos(res.purchase_orders);
    } catch { toast.error("Failed to load purchase orders"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const loadDetail = async (id: string) => {
    setDetailLoading(true);
    try {
      const res = await api.purchaseOrders.get(id);
      setPoDetail(res.purchase_order);
      setSelectedPo(id);
      // Init receive quantities
      const rq: Record<string, number> = {};
      for (const item of res.purchase_order.line_items || []) {
        rq[item.id] = item.received_quantity;
      }
      setReceiveQuantities(rq);
    } catch { toast.error("Failed to load PO details"); }
    finally { setDetailLoading(false); }
  };

  const handleCreate = async () => {
    try {
      await api.purchaseOrders.create(form);
      toast.success("Purchase order created");
      setShowForm(false);
      setForm({ vendor_name: "", notes: "" });
      load();
    } catch { toast.error("Failed to create purchase order"); }
  };

  const handleDelete = async (id: string) => {
    await api.purchaseOrders.delete(id);
    toast.success("Purchase order deleted");
    if (selectedPo === id) { setSelectedPo(null); setPoDetail(null); }
    load();
  };

  const handleAddItem = async () => {
    if (!selectedPo) return;
    if (!newItemForm.description) { toast.error("Description required"); return; }
    try {
      await api.purchaseOrders.lineItems.create(selectedPo, newItemForm);
      toast.success("Line item added");
      setNewItemForm({ product_id: "", description: "", quantity: 1, unit_price: 0 });
      loadDetail(selectedPo);
      load();
    } catch { toast.error("Failed to add line item"); }
  };

  const handleDeleteItem = async (itemId: string) => {
    if (!selectedPo) return;
    await api.purchaseOrders.lineItems.delete(selectedPo, itemId);
    toast.success("Line item removed");
    loadDetail(selectedPo);
    load();
  };

  const handleStatusChange = async (status: string) => {
    if (!selectedPo) return;
    await api.purchaseOrders.status.update(selectedPo, status);
    toast.success(`PO marked as ${status}`);
    loadDetail(selectedPo);
    load();
  };

  const handleReceive = async () => {
    if (!selectedPo || !poDetail?.line_items) return;
    const items = poDetail.line_items.map((item) => ({
      id: item.id,
      received_quantity: receiveQuantities[item.id] ?? item.quantity,
    }));
    await api.purchaseOrders.receive(selectedPo, items);
    toast.success("Items received");
    setReceiveMode(null);
    loadDetail(selectedPo);
    load();
  };

  return (
    <div className="flex gap-6 h-full">
      {/* ── PO list ── */}
      <div className={selectedPo ? "w-1/3 min-w-0" : "w-full"}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Purchase Orders</h1>
            <p className="text-sm text-muted-foreground mt-1">Order parts and inventory</p>
          </div>
          <Button onClick={() => setShowForm(true)} disabled={!!selectedPo}>
            <Plus className="h-4 w-4 mr-1.5" />New PO
          </Button>
        </div>

        {showForm && (
          <Card className="border-primary/30 mb-4">
            <CardHeader><CardTitle>New Purchase Order</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Input placeholder="Vendor Name" value={form.vendor_name}
                onChange={(e) => setForm({ ...form, vendor_name: e.target.value })} />
              <Input placeholder="Notes" value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              <div className="flex gap-2">
                <Button onClick={handleCreate}>Create</Button>
                <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="space-y-2">
          {pos.map((po) => (
            <Card key={po.id}
              className={`cursor-pointer transition-colors ${selectedPo === po.id ? "ring-2 ring-primary" : "hover:bg-muted/50"}`}
              onClick={() => loadDetail(po.id)}>
              <CardContent className="pt-4 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">#{po.po_number}</span>
                    <Badge variant={statusColors[po.status] || "outline"}>{po.status}</Badge>
                  </div>
                  <p className="font-medium mt-1">{po.vendor_name}</p>
                  <p className="text-sm text-muted-foreground">${po.total.toFixed(2)}</p>
                </div>
                <div className="flex items-center gap-2">
                  {selectedPo === po.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </div>
              </CardContent>
            </Card>
          ))}
          {!loading && pos.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-8">No purchase orders yet</p>
          )}
        </div>
      </div>

      {/* ── PO Detail Panel ── */}
      {selectedPo && (
        <div className="flex-1 min-w-0 border-l pl-6">
          {detailLoading ? (
            <p className="text-muted-foreground py-8">Loading...</p>
          ) : poDetail ? (
            <>
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold">PO #{poDetail.po_number}</h2>
                    <Badge variant={statusColors[poDetail.status] || "outline"} className="text-sm">
                      {poDetail.status}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground">{poDetail.vendor_name}</p>
                </div>
                <Button variant="ghost" size="icon" onClick={() => { setSelectedPo(null); setPoDetail(null); }}>
                  <X className="h-4 w-4" />
                </Button>
              </div>

              {/* Action buttons */}
              <div className="flex gap-2 mb-4 flex-wrap">
                {poDetail.status === "draft" && (
                  <Button size="sm" onClick={() => handleStatusChange("sent")}>
                    <SendHorizontal className="h-3.5 w-3.5 mr-1.5" />Mark as Sent
                  </Button>
                )}
                {(poDetail.status === "sent" || poDetail.status === "partial") && (
                  <Button size="sm" onClick={() => setReceiveMode(receiveMode === poDetail.id ? null : poDetail.id)}>
                    <PackageCheck className="h-3.5 w-3.5 mr-1.5" />
                    {receiveMode === poDetail.id ? "Cancel Receive" : "Receive Items"}
                  </Button>
                )}
                {poDetail.status !== "received" && poDetail.status !== "cancelled" && (
                  <Button size="sm" variant="outline" onClick={() => handleStatusChange("cancelled")}>
                    <X className="h-3.5 w-3.5 mr-1.5" />Cancel PO
                  </Button>
                )}
                {poDetail.status === "received" && (
                  <Button size="sm" variant="destructive" onClick={() => handleDelete(poDetail.id)}>
                    <Trash2 className="h-3.5 w-3.5 mr-1.5" />Delete
                  </Button>
                )}
              </div>

              {/* Receipt progress bar */}
              {poDetail.line_items && poDetail.line_items.length > 0 && poDetail.status !== "draft" && (
                <div className="mb-4">
                  <div className="flex justify-between text-xs text-muted-foreground mb-1">
                    <span>Receipt Progress</span>
                    <span>{poDetail.receipt_progress}%</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${poDetail.receipt_progress}%` }} />
                  </div>
                </div>
              )}

              {/* Info card */}
              <Card className="mb-4">
                <CardContent className="pt-4 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Subtotal</span>
                    <span>${poDetail.subtotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-base border-t pt-1 mt-1">
                    <span>Total</span>
                    <span>${poDetail.total.toFixed(2)}</span>
                  </div>
                  {poDetail.notes && (
                    <div className="border-t pt-2 mt-2">
                      <span className="text-muted-foreground">Notes:</span>
                      <p className="mt-0.5">{poDetail.notes}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Line items */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">Line Items</h3>
                  {poDetail.status !== "received" && poDetail.status !== "cancelled" && (
                    <Button size="sm" variant="outline" onClick={() => setNewItemForm({ ...newItemForm, description: "" })}>
                      <Plus className="h-3.5 w-3.5 mr-1" />Add Item
                    </Button>
                  )}
                </div>

                {/* Add item form */}
                {newItemForm.description !== "" && poDetail.status !== "received" && poDetail.status !== "cancelled" && (
                  <Card className="border-primary/30 mb-3">
                    <CardContent className="pt-3 space-y-2">
                      <Input placeholder="Description (required)" value={newItemForm.description}
                        onChange={(e) => setNewItemForm({ ...newItemForm, description: e.target.value })} />
                      <div className="flex gap-2">
                        <Input type="number" placeholder="Qty" value={newItemForm.quantity}
                          onChange={(e) => setNewItemForm({ ...newItemForm, quantity: Number(e.target.value) })} />
                        <Input type="number" step="0.01" placeholder="Unit Price" value={newItemForm.unit_price}
                          onChange={(e) => setNewItemForm({ ...newItemForm, unit_price: Number(e.target.value) })} />
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" onClick={handleAddItem}>Add</Button>
                        <Button size="sm" variant="outline" onClick={() => setNewItemForm({ product_id: "", description: "", quantity: 1, unit_price: 0 })}>Cancel</Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Items list */}
                <div className="space-y-2">
                  {(poDetail.line_items || []).map((item) => (
                    <Card key={item.id}>
                      <CardContent className="pt-3">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium">{item.description}</p>
                            <p className="text-sm text-muted-foreground">
                              {item.quantity} × ${item.unit_price.toFixed(2)} = ${item.total.toFixed(2)}
                            </p>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                              <span>Received: {item.received_quantity}/{item.quantity}</span>
                              <div className="h-1.5 w-20 bg-muted rounded-full overflow-hidden">
                                <div className="h-full bg-green-500 rounded-full"
                                  style={{ width: `${Math.min(100, (item.received_quantity / item.quantity) * 100)}%` }} />
                              </div>
                            </div>
                          </div>

                          {/* Receive mode controls */}
                          {receiveMode === poDetail.id && poDetail.status !== "received" && (
                            <div className="flex items-center gap-2 ml-3">
                              <Input type="number" className="w-20 h-8 text-xs"
                                min={0} max={item.quantity}
                                value={receiveQuantities[item.id] ?? item.received_quantity}
                                onChange={(e) => setReceiveQuantities({ ...receiveQuantities, [item.id]: Number(e.target.value) })} />
                            </div>
                          )}

                          {/* Delete button */}
                          {poDetail.status === "draft" && (
                            <Button size="icon" variant="ghost" className="ml-2"
                              onClick={() => handleDeleteItem(item.id)}>
                              <Trash2 className="h-3 w-3 text-destructive" />
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                  {(!poDetail.line_items || poDetail.line_items.length === 0) && (
                    <p className="text-sm text-muted-foreground text-center py-4">No line items</p>
                  )}
                </div>
              </div>

              {/* Receive confirmation */}
              {receiveMode === poDetail.id && (
                <Card className="border-green-500/30 bg-green-500/5">
                  <CardContent className="pt-4">
                    <p className="text-sm font-medium mb-2">Confirm receipt of items?</p>
                    <p className="text-xs text-muted-foreground mb-3">
                      Stock levels will be updated and inventory adjustments created.
                    </p>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleReceive}>
                        <PackageCheck className="h-3.5 w-3.5 mr-1" />Confirm Receipt
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setReceiveMode(null)}>Cancel</Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
