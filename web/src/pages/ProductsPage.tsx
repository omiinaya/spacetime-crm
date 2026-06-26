import { useState, useEffect } from "react";
import { api, Product } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Package, Plus, Search, Edit2, Trash2 } from "lucide-react";
import { toast } from "sonner";

const emptyForm: Partial<Product> = { name: "", sku: "", description: "", category: "", price: 0, cost: 0, quantity_on_hand: 0 };

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<Product>>({ ...emptyForm });

  const load = async () => {
    try {
      const res = await api.products.list(search);
      setProducts(res.products);
    } catch { toast.error("Failed to load products"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [search]);

  const handleSubmit = async () => {
    try {
      if (editId) {
        await api.products.updateQuantity(editId, form.quantity_on_hand || 0);
        toast.success("Product updated");
      } else {
        await api.products.create(form);
        toast.success("Product created");
      }
      setShowForm(false);
      setEditId(null);
      setForm({ ...emptyForm });
      load();
    } catch { toast.error("Failed to save product"); }
  };

  const handleEdit = (p: Product) => {
    setForm(p);
    setEditId(p.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await api.products.delete(id);
      toast.success("Product deleted");
      load();
    } catch { toast.error("Failed to delete"); }
  };

  const lowStock = (p: Product) => p.quantity_on_hand <= p.min_stock && p.min_stock > 0;

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Products</h1>
          <p className="text-sm text-muted-foreground mt-1">Inventory management</p>
        </div>
        <Button onClick={() => { setForm({ ...emptyForm }); setEditId(null); setShowForm(true); }}>
          <Plus className="h-4 w-4 mr-1.5" />Add Product
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search products..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
      </div>

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader><CardTitle>{editId ? "Edit Product" : "New Product"}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <Input placeholder="SKU" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
              <Input placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
              <Input placeholder="Location" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
              <Input type="number" placeholder="Price" value={form.price} onChange={(e) => setForm({ ...form, price: +e.target.value })} />
              <Input type="number" placeholder="Cost" value={form.cost} onChange={(e) => setForm({ ...form, cost: +e.target.value })} />
              <Input type="number" placeholder="Qty on Hand" value={form.quantity_on_hand} onChange={(e) => setForm({ ...form, quantity_on_hand: +e.target.value })} />
              <Input type="number" placeholder="Min Stock" value={form.min_stock} onChange={(e) => setForm({ ...form, min_stock: +e.target.value })} />
            </div>
            <Input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <div className="flex gap-2">
              <Button onClick={handleSubmit}>{editId ? "Update" : "Create"}</Button>
              <Button variant="outline" onClick={() => { setShowForm(false); setEditId(null); }}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {products.map((p) => (
          <Card key={p.id} className={lowStock(p) ? "border-destructive/40" : ""}>
            <CardContent className="pt-4">
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Package className="h-4 w-4 text-muted-foreground" />
                    <p className="font-medium truncate">{p.name}</p>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{p.sku} — {p.category}</p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button size="icon" variant="ghost" onClick={() => handleEdit(p)}><Edit2 className="h-3.5 w-3.5" /></Button>
                  <Button size="icon" variant="ghost" onClick={() => handleDelete(p.id)}><Trash2 className="h-3.5 w-3.5 text-destructive" /></Button>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">${p.price.toFixed(2)}</span>
                <span className={lowStock(p) ? "text-destructive font-medium" : "text-muted-foreground"}>
                  Stock: {p.quantity_on_hand}
                  {lowStock(p) && " ⚠"}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
