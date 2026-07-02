import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api, Product } from "../lib/api";
import { usePagination } from "../lib/usePagination";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import Pagination from "../components/Pagination";
import { Package, Plus, Search, ClipboardList, Scan, ScanLine, AlertTriangle, Printer, ArrowRightLeft } from "lucide-react";
import { printBarcodeLabel } from "../components/BarcodeLabel";
import { toast } from "sonner";
import { useAuth } from "../lib/auth";

const PAGE_SIZE = 25;

const emptyForm: Partial<Product> = { name: "", sku: "", barcode: "", description: "", category: "", price: 0, cost: 0, quantity_on_hand: 0 };

const reasonColors: Record<string, string> = {
  received: "text-green-400",
  sold: "text-red-400",
  damaged: "text-orange-400",
  returned: "text-blue-400",
  counted: "text-purple-400",
  transferred: "text-cyan-400",
};

export default function ProductsPage() {
  const pag = usePagination(PAGE_SIZE);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<Product>>({ ...emptyForm });
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [adjForm, setAdjForm] = useState({ quantity_change: 0, reason: "received", reference_id: "", notes: "" });
  const { user } = useAuth();
  const [scanning, setScanning] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [barcodeLookup, setBarcodeLookup] = useState("");

  const barcodeDetectorSupported = typeof window !== "undefined" && "BarcodeDetector" in window;

  const { data: categories } = useQuery({
    queryKey: ["product-categories"],
    queryFn: async () => {
      const res = await api.products.categories();
      return res.categories;
    },
    staleTime: 60000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["products", { search, category: categoryFilter, offset: pag.offset }],
    queryFn: async () => {
      const res = await api.products.list(search, categoryFilter, pag.offset, PAGE_SIZE);
      return res;
    },
    select: (res) => {
      pag.setTotal(res.total);
      return { products: res.products };
    },
  });

  const products = data?.products ?? [];

  // Adjustments query — active when product selected
  const { data: adjData } = useQuery({
    queryKey: ["product-adjustments", selectedProduct?.id],
    queryFn: async () => {
      const res = await api.products.adjustments.list(selectedProduct!.id);
      return res.adjustments;
    },
    enabled: !!selectedProduct,
  });
  const adjustments = adjData ?? [];

  const handleSearch = (val: string) => {
    setSearch(val);
    pag.reset();
  };

  const barcodeLookupMutation = useMutation({
    mutationFn: async () => {
      if (!barcodeLookup.trim()) throw new Error("No barcode");
      return api.products.byBarcode(barcodeLookup.trim());
    },
    onSuccess: (data) => {
      setSelectedProduct(data.product);
      toast.success(`Found: ${data.product.name}`);
      setBarcodeLookup("");
    },
    onError: () => toast.error("No product found with this barcode"),
  });

  const handleBarcodeLookup = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") barcodeLookupMutation.mutate();
  };

  const createMutation = useMutation({
    mutationFn: () => api.products.create(form),
    onSuccess: () => {
      toast.success("Product created");
      setShowForm(false);
      setForm({ ...emptyForm });
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
    onError: () => toast.error("Failed to save product"),
  });

  const adjustMutation = useMutation({
    mutationFn: () => {
      if (!selectedProduct || !user) throw new Error("No product or user");
      return api.products.adjustments.create(selectedProduct.id, {
        ...adjForm,
        user_id: user.id,
      });
    },
    onSuccess: () => {
      toast.success("Stock adjusted");
      setAdjForm({ quantity_change: 0, reason: "received", reference_id: "", notes: "" });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["product-adjustments", selectedProduct?.id] });
    },
    onError: () => toast.error("Failed to adjust stock"),
  });

  // Transfer stock state + mutation
  const [transferForm, setTransferForm] = useState({ destProductId: "", quantity: 1, notes: "" });
  const [transferSearch, setTransferSearch] = useState("");

  const { data: transferProducts } = useQuery({
    queryKey: ["products", "transfer-search", transferSearch],
    queryFn: async () => {
      if (!transferSearch) return { products: [] as Product[] };
      const res = await api.products.list(transferSearch, undefined, 0, 20);
      return res;
    },
    enabled: transferSearch.length >= 1,
  });

  const transferMutation = useMutation({
    mutationFn: () => {
      if (!selectedProduct || !transferForm.destProductId) throw new Error("Select a destination product");
      return api.products.transfer({
        source_product_id: selectedProduct.id,
        destination_product_id: transferForm.destProductId,
        quantity: transferForm.quantity,
        notes: transferForm.notes,
      });
    },
    onSuccess: (res) => {
      toast.success(`Transferred ${res.quantity ?? 0} units`);
      setTransferForm({ destProductId: "", quantity: 1, notes: "" });
      setTransferSearch("");
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["product-adjustments", selectedProduct?.id] });
    },
    onError: () => toast.error("Transfer failed"),
  });

  const { data: lowStockData } = useQuery({
    queryKey: ["products", "low-stock"],
    queryFn: () => api.products.lowStock.list(),
    refetchInterval: 60000,
  });

  const lowStock = lowStockData?.products ?? [];
  const lowStockCount = lowStockData?.count ?? 0;

  const notifyLowStockMutation = useMutation({
    mutationFn: () => api.products.lowStock.notify(),
    onSuccess: (res) => {
      if ((res.count ?? 0) > 0) {
        toast.success(`Low stock alert sent to admin (${res.count ?? 0} products)`);
      } else {
        toast.info("No low stock products to report");
      }
    },
    onError: () => toast.error("Failed to send low stock notification"),
  });

  const startScanner = async () => {
    setScanning(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        scanLoop();
      }
    } catch {
      toast.error("Camera access denied or unavailable");
      setScanning(false);
    }
  };

  const stopScanner = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setScanning(false);
  };

  const scanLoop = () => {
    if (!scanning || !videoRef.current || !barcodeDetectorSupported) return;
    const detector = new (window as any).BarcodeDetector({ formats: ["qr_code", "ean_13", "ean_8", "code_128", "code_39", "upc_a", "upc_e", "codabar", "data_matrix"] });
    detector.detect(videoRef.current).then((barcodes: any[]) => {
      if (barcodes.length > 0) {
        const code = barcodes[0].rawValue;
        setForm({ ...form, barcode: code });
        toast.success("Barcode detected: " + code);
        stopScanner();
        return;
      }
      if (scanning) requestAnimationFrame(scanLoop);
    }).catch(() => {
      if (scanning) requestAnimationFrame(scanLoop);
    });
  };

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  const handleSubmit = () => createMutation.mutate();

  const adjustStock = () => adjustMutation.mutate();

  const viewProduct = (p: Product) => {
    setSelectedProduct(p);
  };

  const fmtDate = (ts: number) => new Date(ts).toLocaleString();

  return (
    <>
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Products</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage inventory and stock</p>
        </div>
        <Button onClick={() => { setShowForm(true); setEditId(null); setForm({ ...emptyForm }); }}>
          <Plus className="h-4 w-4 mr-1.5" /> Add Product
        </Button>
      </div>

      {/* Search + category filter */}
      <div className="flex gap-2 items-center flex-wrap">
        <Input
          placeholder="Search products..."
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="max-w-full sm:max-w-sm"
        />
        <select
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); pag.reset(); }}
          className="h-9 rounded-md border border-input bg-background px-3 text-xs outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All categories</option>
          {categories?.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <div className="flex items-center gap-1 border rounded-md px-2 py-1 bg-muted/30 max-w-full sm:max-w-[200px] flex-1 sm:flex-none">
          <Scan className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <input
            type="text"
            placeholder="Scan barcode..."
            value={barcodeLookup}
            onChange={(e) => setBarcodeLookup(e.target.value)}
            onKeyDown={handleBarcodeLookup}
            className="bg-transparent border-none outline-none text-xs w-full py-0.5"
          />
        </div>
      </div>

      {lowStockCount > 0 && (
        <div className="flex items-center justify-between rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-400" />
            <p className="text-sm text-amber-300">
              <span className="font-semibold">{lowStockCount}</span> product{lowStockCount !== 1 ? "s" : ""} below minimum stock
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="border-amber-500/40 text-amber-300 hover:bg-amber-500/20"
              onClick={() => document.getElementById("low-stock-list")?.scrollIntoView({ behavior: "smooth" })}
            >
              View
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="border-amber-500/40 text-amber-300 hover:bg-amber-500/20"
              onClick={() => notifyLowStockMutation.mutate()}
              disabled={notifyLowStockMutation.isPending}
            >
              {notifyLowStockMutation.isPending ? "Sending..." : "Notify Admin"}
            </Button>
          </div>
        </div>
      )}

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader><CardTitle>{editId ? "Edit Product" : "New Product"}</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Input placeholder="SKU" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
            <div className="col-span-2">
              <Input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <Input placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
            <Input placeholder="Price" type="number" value={form.price} onChange={(e) => setForm({ ...form, price: parseFloat(e.target.value) || 0 })} />
            <Input placeholder="Cost" type="number" value={form.cost} onChange={(e) => setForm({ ...form, cost: parseFloat(e.target.value) || 0 })} />
            <Input placeholder="Qty on hand" type="number" value={form.quantity_on_hand} onChange={(e) => setForm({ ...form, quantity_on_hand: parseFloat(e.target.value) || 0 })} />
            <Input placeholder="Min stock" type="number" value={form.min_stock ?? 0} onChange={(e) => setForm({ ...form, min_stock: parseFloat(e.target.value) || 0 })} />
            <Input placeholder="Location" value={form.location ?? ""} onChange={(e) => setForm({ ...form, location: e.target.value })} />
            <div className="col-span-2 flex gap-2">
              <div className="flex-1 flex gap-2">
                <Input
                  placeholder="Barcode"
                  value={form.barcode}
                  onChange={(e) => setForm({ ...form, barcode: e.target.value })}
                  className="flex-1"
                />
                {barcodeDetectorSupported && (
                  <Button type="button" variant="outline" size="icon" onClick={startScanner} title="Scan barcode">
                    <Scan className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
            {scanning && (
              <div className="col-span-2 relative rounded-lg overflow-hidden bg-black">
                <video ref={videoRef} className="w-full h-48 object-cover" />
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <ScanLine className="h-16 w-16 text-white/40" />
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="absolute top-2 right-2 bg-black/50 text-white border-white/30"
                  onClick={stopScanner}
                >
                  Cancel
                </Button>
                <p className="absolute bottom-2 left-2 text-xs text-white/60 bg-black/40 px-2 py-1 rounded">
                  Point camera at barcode
                </p>
              </div>
            )}
            <div className="col-span-2 flex gap-2">
              <Button onClick={handleSubmit}>{editId ? "Update" : "Create"}</Button>
              <Button variant="outline" onClick={() => { setShowForm(false); setEditId(null); }}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Product list */}
        <div className={`space-y-3 ${selectedProduct ? "hidden lg:block" : ""}`}>
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
                      {p.min_stock > 0 && p.quantity_on_hand <= p.min_stock && (<Badge variant="destructive" className="text-[10px] px-1.5 py-0">Low</Badge>)}
                    </div>
                    {p.category && <p className="text-xs text-muted-foreground mt-1">{p.category}</p>}
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold">${p.price.toFixed(2)}</p>
                    <p className={`text-xs ${p.quantity_available <= 0 ? "text-destructive" : "text-muted-foreground"}`}>
                      {p.quantity_on_hand} in stock
                    </p>
                  </div>
                  {p.barcode && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="ml-2 shrink-0"
                      onClick={(e) => { e.stopPropagation(); printBarcodeLabel(p.barcode, p.name, p.price, p.sku); }}
                      title="Print barcode label"
                    >
                      <Printer className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Detail panel */}
        {selectedProduct && (
          <div className="space-y-4">
            {/* Back button (mobile) */}
            <button
              onClick={() => setSelectedProduct(null)}
              className="lg:hidden text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              ← Back to list
            </button>
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
                {selectedProduct.min_stock > 0 && (
                  <div className="flex items-center justify-between text-sm px-2 py-1.5 rounded bg-muted/50">
                    <span>Min Stock:</span>
                    <span className={`font-medium ${selectedProduct.quantity_on_hand <= selectedProduct.min_stock ? "text-destructive" : "text-green-400"}`}>
                      {selectedProduct.min_stock}
                    </span>
                  </div>
                )}
                <p className="text-sm">Price: <span className="font-medium">${selectedProduct.price.toFixed(2)}</span> &middot; Cost: <span className="font-medium">${selectedProduct.cost.toFixed(2)}</span></p>
                {selectedProduct.barcode && (
                  <p className="text-sm">Barcode: <span className="font-mono text-xs text-muted-foreground">{selectedProduct.barcode}</span>
                    <Button variant="ghost" size="icon" className="ml-1 inline-flex h-5 w-5 align-middle"
                      onClick={() => printBarcodeLabel(selectedProduct.barcode, selectedProduct.name, selectedProduct.price, selectedProduct.sku)}
                      title="Print barcode label">
                      <Printer className="h-3 w-3" />
                    </Button>
                  </p>
                )}
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

            {/* Stock transfer */}
            <Card>
              <CardHeader><CardTitle><ArrowRightLeft className="h-4 w-4 inline mr-1.5" />Transfer Stock</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  Move stock from <strong>{selectedProduct.name}</strong> to another product
                </p>
                <div>
                  <Input
                    placeholder="Search destination product..."
                    value={transferSearch}
                    onChange={(e) => setTransferSearch(e.target.value)}
                  />
                  {transferSearch.length >= 1 && (
                    <div className="mt-1 max-h-32 overflow-y-auto border border-border rounded-md bg-card">
                      {(transferProducts?.products ?? []).filter(p => p.id !== selectedProduct.id).map((p) => (
                        <button
                          key={p.id}
                          className={`w-full text-left px-3 py-1.5 text-sm hover:bg-muted/50 transition-colors ${transferForm.destProductId === p.id ? "bg-primary/10 font-medium" : ""}`}
                          onClick={() => { setTransferForm({ ...transferForm, destProductId: p.id }); setTransferSearch(p.name); }}
                        >
                          {p.name} <span className="text-xs text-muted-foreground">({p.quantity_on_hand} in stock)</span>
                        </button>
                      ))}
                      {(transferProducts?.products ?? []).filter(p => p.id !== selectedProduct.id).length === 0 && (
                        <p className="px-3 py-1.5 text-xs text-muted-foreground">No matching products</p>
                      )}
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Quantity</label>
                    <Input
                      type="number"
                      min={1}
                      value={transferForm.quantity}
                      onChange={(e) => setTransferForm({ ...transferForm, quantity: Math.max(1, parseInt(e.target.value) || 1) })}
                    />
                  </div>
                  <div className="flex items-end">
                    <span className="text-xs text-muted-foreground pb-2">Max: {selectedProduct.quantity_on_hand}</span>
                  </div>
                </div>
                <Input
                  placeholder="Transfer notes (optional)"
                  value={transferForm.notes}
                  onChange={(e) => setTransferForm({ ...transferForm, notes: e.target.value })}
                />
                <Button
                  onClick={() => transferMutation.mutate()}
                  disabled={!transferForm.destProductId || transferMutation.isPending}
                >
                  {transferMutation.isPending ? "Transferring..." : "Transfer"}
                </Button>
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

      <Pagination
        page={pag.page}
        totalPages={pag.totalPages}
        total={pag.total}
        hasPrev={pag.hasPrev}
        hasNext={pag.hasNext}
        onPrev={pag.prevPage}
        onNext={pag.nextPage}
        onGoToPage={pag.goToPage}
      />
    </>
  );
}
