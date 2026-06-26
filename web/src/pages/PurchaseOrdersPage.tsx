import { useState, useEffect } from "react";
import { api, PurchaseOrder } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { ShoppingCart, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

const statusColors: Record<string, "outline" | "default" | "success" | "destructive"> = {
  draft: "outline",
  sent: "default",
  received: "success",
  cancelled: "destructive",
};

export default function PurchaseOrdersPage() {
  const [pos, setPos] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ vendor_name: "", notes: "" });

  const load = async () => {
    try {
      const res = await api.purchaseOrders.list();
      setPos(res.purchase_orders);
    } catch { toast.error("Failed to load purchase orders"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

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
    load();
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Purchase Orders</h1>
          <p className="text-sm text-muted-foreground mt-1">Order parts and inventory</p>
        </div>
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-1.5" />New PO</Button>
      </div>

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader><CardTitle>New Purchase Order</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Input placeholder="Vendor Name" value={form.vendor_name} onChange={(e) => setForm({ ...form, vendor_name: e.target.value })} />
            <Input placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            <div className="flex gap-2">
              <Button onClick={handleCreate}>Create</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {pos.map((po) => (
          <Card key={po.id}>
            <CardContent className="pt-4 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">#{po.po_number}</span>
                  <Badge variant={statusColors[po.status] || "outline"}>{po.status}</Badge>
                </div>
                <p className="font-medium mt-1">{po.vendor_name}</p>
                <p className="text-sm text-muted-foreground">${po.total.toFixed(2)}</p>
              </div>
              <Button size="icon" variant="ghost" onClick={() => handleDelete(po.id)}><Trash2 className="h-3.5 w-3.5 text-destructive" /></Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
