import { useState, useEffect } from "react";
import { api, Product, InventoryAdjustment } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Package, Plus, Search, ClipboardList } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../lib/auth";

const emptyForm: Partial<Product> = { name: "", sku: "", description: "", category: "", price: 0, cost: 0, quantity_on_hand: 0 };

const reasonColors: Record<string, string> = {
  received: "text-green-400",
  sold: "text-red-400",
  damaged: "text-orange-400",
  returned: "text-blue-400",
  counted: "text-purple-400",
  transferred: "text-cyan-400",
};

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<Product>>({ ...emptyForm });
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [adjustments, setAdjustments] = useState<InventoryAdjustment[]>([]);
  const [adjForm, setAdjForm] = useState({ quantity_change: 0, reason: "received", reference_id: "", notes: "" });
  const { user } = useAuth();

  const load = async () => {
    try {
      const res = await api.products.list(search);
      setProducts(res.products);
    } catch { toast.error("Failed to load products"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [search]);

  const loadAdjustments = async (productId: string) => {
    try {
      const res = await api.products.adjustments.list(productId);
      setAdjustments(res.adjustments);
    } catch { setAdjustments([]); }
  };

  const handleSubmit = async () => {
    try {
      await api.products.create(form);
      toast.success("Product created");
      setShowForm(false);
      setForm({ ...emptyForm });
      load();
    } catch { toast.error("Failed to save product"); }
  };

  const adjustStock = async () => {
    if (!selectedProduct || !user) return;
    try {
      await api.products.adjustments.create(selectedProduct.id, {
        ...adjForm,
        user_id: user.id,
      });
      toast.success("Stock adjusted");
      setAdjForm({ quantity_change: 0, reason: "received", reference_id: "", notes: "" });
      load();
      loadAdjustments(selectedProduct.id);
    } catch { toast.error("Failed to adjust stock"); }
  };

  const viewProduct = async (p: Product) => {
    setSelectedProduct(p);
    await loadAdjustments(p.id);
  };

  const fmtDate = (ts: number) => new Date(ts).toLocaleString();

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Products</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage inventory and stock</p>
        </div>
        <Button onClick={() => { setShowForm(true); setEditId(null); setForm({ ...emptyForm }); }}>
          <Plus className="h-4 w-4 mr-1.5" /> Add Product
        </Button>
      </div>

      {/* Search */}
      <Input
        placeholder="Search products..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-sm"
      />

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader><CardTitle>{editId ? "Edit Product" : "New Product"}</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <Input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Input placeholder="SKU" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
            <div className="col-span-2">
              <Input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <Input placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
            <Input placeholder="Price" type="number" value={form.price} onChange={(e) => setForm({ ...form, price: parseFloat(e.target.value) || 0 })} />
            <Input placeholder="Cost" type="number" value={form.cost} onChange={(e) => setForm({ ...form, cost: parseFloat(e.target.value) || 0 })} />
            <Input placeholder="Qty on hand" type="number" value={form.quantity_on_hand} onChange={(e) => setForm({ ...form, quantity_on_hand: parseFloat(e.target.value) || 0 })} />
            <div className="col-span-2 flex gap-2">
              <Button onClick={handleSubmit}>{editId ? "Update" : "Create"}</Button>
              <Button variant="outline" onClick={() => { setShowForm(false); setEditId(null); }}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Product list */}
        <div className="space-y-3">
          {products.map((p) => (
            <Card
              key={p.id}
              className={`cursor-pointer transition-colors ${selectedProduct?.id === p.id ? "border-primary" : "hover:border-primary/30"}`}
              onClick={() => viewProduct(p)}
            >
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Package className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{p.name}</span>
                      {p.sku && <span className="text-xs text-muted-foreground">{p.sku}</span>}
                    </div>
                    {p.category && <p className="text-xs text-muted-foreground mt-1">{p.category}</p>}
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold">${p.price.toFixed(2)}</p>
                    <p className={`text-xs ${p.quantity_available <= 0 ? "text-destructive" : "text-muted-foreground"}`}>
                      {p.quantity_on_hand} in stock
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Detail panel */}
        {selectedProduct && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>{selectedProduct.name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold">{selectedProduct.quantity_on_hand}</p>
                    <p className="text-xs text-muted-foreground">On Hand</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{selectedProduct.quantity_committed}</p>
                    <p className="text-xs text-muted-foreground">Committed</p>
                  </div>
                  <div>
                    <p className={`text-2xl font-bold ${selectedProduct.quantity_available <= 0 ? "text-destructive" : ""}`}>
                      {selectedProduct.quantity_available}
                    </p>
                    <p className="text-xs text-muted-foreground">Available</p>
                  </div>
                </div>
                <p className="text-sm">Price: <span className="font-medium">${selectedProduct.price.toFixed(2)}</span> &middot; Cost: <span className="font-medium">${selectedProduct.cost.toFixed(2)}</span></p>
                {selectedProduct.description && <p className="text-sm text-muted-foreground">{selectedProduct.description}</p>}
              </CardContent>
            </Card>

            {/* Stock adjustment */}
            <Card>
              <CardHeader><CardTitle><ClipboardList className="h-4 w-4 inline mr-1.5" />Adjust Stock</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="number"
                    placeholder="Quantity change"
                    value={adjForm.quantity_change}
                    onChange={(e) => setAdjForm({ ...adjForm, quantity_change: parseFloat(e.target.value) || 0 })}
                  />
                  <Select value={adjForm.reason} onChange={(e) => setAdjForm({ ...adjForm, reason: e.target.value })}>
                    <option value="received">Received</option>
                    <option value="sold">Sold</option>
                    <option value="damaged">Damaged</option>
                    <option value="returned">Returned</option>
                    <option value="counted">Counted</option>
                    <option value="transferred">Transferred</option>
                  </Select>
                </div>
                <Input
                  placeholder="Reference (e.g. PO-1234)"
                  value={adjForm.reference_id}
                  onChange={(e) => setAdjForm({ ...adjForm, reference_id: e.target.value })}
                />
                <Input
                  placeholder="Notes"
                  value={adjForm.notes}
                  onChange={(e) => setAdjForm({ ...adjForm, notes: e.target.value })}
                />
                <Button onClick={adjustStock}>Apply Adjustment</Button>
              </CardContent>
            </Card>

            {/* History */}
            <Card>
              <CardHeader><CardTitle>Adjustment History</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {adjustments.length === 0 && (
                    <p className="text-sm text-muted-foreground">No adjustments yet</p>
                  )}
                  {adjustments.slice().reverse().map((a) => (
                    <div key={a.id} className="flex items-center justify-between text-sm p-2 rounded bg-muted/50">
                      <div className="min-w-0 flex-1">
                        <span className={`font-medium ${a.quantity_change > 0 ? "text-green-400" : "text-red-400"}`}>
                          {a.quantity_change > 0 ? "+" : ""}{a.quantity_change}
                        </span>
                        <span className={`ml-2 text-xs ${reasonColors[a.reason] || ""}`}>{a.reason}</span>
                        {a.reference_id && <span className="ml-2 text-xs text-muted-foreground">{a.reference_id}</span>}
                        <p className="text-xs text-muted-foreground mt-0.5">{a.notes}</p>
                      </div>
                      <span className="text-xs text-muted-foreground ml-2 shrink-0">{fmtDate(a.created_at)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </>
  );
}
