import { useState, useCallback, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, POSCounterSale, POSCounterSaleDetail, POSCounterSaleLineItem, POSAddItemPayload } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import {
  ShoppingCart, Printer, Search, X, Plus, Minus,
  DollarSign, Receipt, RotateCcw, Trash2, CreditCard,
  Banknote, Loader2, ArrowLeft, Check, FileDown, Lock, Unlock,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../lib/auth";

interface CartItem {
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: number;
}

interface ReceiptData {
  sale: POSCounterSale;
  items: POSCounterSaleLineItem[];
}

export default function PosPage() {
  const queryClient = useQueryClient();
  const scanRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"sale" | "history" | "receipt">("sale");
  const [customerName, setCustomerName] = useState("Walk-in");
  const [customerId, setCustomerId] = useState("");
  const [customerSearch, setCustomerSearch] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<"cash" | "card">("cash");
  const [amountTendered, setAmountTendered] = useState("");
  const [taxRate, setTaxRate] = useState("8.25");
  const [discount, setDiscount] = useState("0");
  const [searchQuery, setSearchQuery] = useState("");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [scanning, setScanning] = useState(false);
  const [lastReceipt, setLastReceipt] = useState<ReceiptData | null>(null);
  const [refunding, setRefunding] = useState(false);
  const [pinVerified, setPinVerified] = useState(false);
  const [pinInput, setPinInput] = useState("");
  const [pinError, setPinError] = useState("");
  const [pinVerifying, setPinVerifying] = useState(false);
  const [locked, setLocked] = useState(false);
  const pinRef = useRef<HTMLInputElement>(null);
  const { user, token } = useAuth();

  // ── Check if user has a PIN set ──
  const [hasPin, setHasPin] = useState<boolean | null>(null);
  useEffect(() => {
    if (!token) return;
    fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setHasPin(data.has_pin ?? false))
      .catch(() => setHasPin(false));
  }, [token]);

  // ── PIN verification ──
  const handlePinSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pinInput || pinInput.length < 4) {
      setPinError("PIN must be at least 4 digits");
      return;
    }
    if (!user) {
      setPinError("Not authenticated");
      return;
    }
    setPinVerifying(true);
    setPinError("");
    try {
      await api.auth.posLogin(user.id, pinInput);
      setPinVerified(true);
      setLocked(false);
      setPinInput("");
      setPinError("");
    } catch (err: any) {
      setPinError("Invalid PIN — try again");
      setPinInput("");
      pinRef.current?.focus();
    } finally {
      setPinVerifying(false);
    }
  }, [pinInput, user]);

  // ── Product search ──
  const { data: searchResults } = useQuery({
    queryKey: ["pos-products", searchQuery],
    queryFn: () =>
      api.products.list(searchQuery, 0, 20).then((r) => r.products),
    enabled: searchQuery.length >= 1,
  });

  // ── Customer search ──
  const { data: customerResults } = useQuery({
    queryKey: ["pos-customers", customerSearch],
    queryFn: () =>
      api.customers.list(customerSearch, 0, 10).then((r) => r.customers),
    enabled: customerSearch.length >= 1,
  });

  // ── Sale history ──
  const { data: salesHistory, isLoading: loadingHistory } = useQuery({
    queryKey: ["pos-sales"],
    queryFn: () => api.pos.receipts(0, 50).then((r) => r.receipts),
    enabled: mode === "history",
  });

  // ── Create sale mutation ──
  const createMutation = useMutation({
    mutationFn: (data: { saleId: string; items: CartItem[] }) =>
      api.pos.create({
        customer_name: customerName,
        payment_method: paymentMethod,
        amount_tendered: parseFloat(amountTendered) || 0,
        tax_rate: parseFloat(taxRate) || 0,
        discount_amount: parseFloat(discount) || 0,
      }),
  });

  // ── Add item mutation ──
  const addItemMutation = useMutation({
    mutationFn: (payload: POSAddItemPayload) => api.pos.addItem(payload),
  });

  const handleSaleComplete = useCallback(async () => {
    if (cart.length === 0) {
      toast.error("Cart is empty");
      return;
    }

    // 1. Create the sale
    const createRes = await api.pos.create({
      customer_id: customerId,
      customer_name: customerName,
      payment_method: paymentMethod,
      amount_tendered: parseFloat(amountTendered) || 0,
      tax_rate: parseFloat(taxRate) || 0,
      discount_amount: parseFloat(discount) || 0,
    });
    if (!createRes.ok) {
      toast.error("Failed to create sale");
      return;
    }

    // 2. Get the latest sale (just created)
    const listRes = await api.pos.list(0, 1);
    const saleId = listRes.sales[0]?.id;
    if (!saleId) {
      toast.error("No sale found after create");
      return;
    }

    // 3. Add all cart items
    for (const item of cart) {
      await api.pos.addItem({
        sale_id: saleId,
        product_id: item.product_id,
        product_name: item.product_name,
        sku: item.sku,
        quantity: item.quantity,
        unit_price: item.unit_price,
      });
    }

    // 4. Fetch completed receipt
    const detailRes = await api.pos.get(saleId);
    setLastReceipt({
      sale: detailRes.sale,
      items: detailRes.sale.line_items,
    });

    // 5. Reset cart
    setCart([]);
    setAmountTendered("");
    setCustomerId("");
    setCustomerName("Walk-in");
    setCustomerSearch("");
    setMode("receipt");
    queryClient.invalidateQueries({ queryKey: ["pos-sales"] });
    toast.success(`Sale complete — Receipt #${detailRes.sale.receipt_number}`);
  }, [cart, customerName, paymentMethod, amountTendered, taxRate, discount, queryClient]);

  // ── Add to cart from search result ──
  const addToCart = useCallback((product: { id: string; name: string; sku: string; price: number }) => {
    setCart((prev) => {
      const existing = prev.find((c) => c.product_id === product.id);
      if (existing) {
        return prev.map((c) =>
          c.product_id === product.id
            ? { ...c, quantity: c.quantity + 1 }
            : c
        );
      }
      return [
        ...prev,
        {
          product_id: product.id,
          product_name: product.name,
          sku: product.sku || "",
          quantity: 1,
          unit_price: product.price,
        },
      ];
    });
    setSearchQuery("");
    scanRef.current?.focus();
    toast(`${product.name} added`);
  }, []);

  // ── Update cart quantity ──
  const updateQty = useCallback((productId: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((c) =>
          c.product_id === productId
            ? { ...c, quantity: Math.max(0, c.quantity + delta) }
            : c
        )
        .filter((c) => c.quantity > 0)
    );
  }, []);

  // ── Barcode scan handler ──
  useEffect(() => {
    const scanInput = scanRef.current;
    if (!scanInput || scanning) return;

    let scanBuffer = "";
    let scanTimer: ReturnType<typeof setTimeout>;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore when typing in other inputs
      if (e.target !== scanInput) return;

      if (e.key === "Enter") {
        e.preventDefault();
        const barcode = scanBuffer.trim();
        scanBuffer = "";
        if (!barcode) return;

        api.products.byBarcode(barcode).then((res) => {
          addToCart(res.product);
        }).catch(() => {
          // Not found by exact barcode — fall back to SKU search
          api.products.list(barcode, 0, 5).then((res) => {
            const found = res.products.find((p) => p.sku === barcode);
            if (found) {
              addToCart(found);
            } else {
              toast.error(`No product found: ${barcode}`);
            }
          });
        });
      } else if (e.key.length === 1) {
        scanBuffer += e.key;
        clearTimeout(scanTimer);
        scanTimer = setTimeout(() => { scanBuffer = ""; }, 200);
      }
    };

    scanInput.addEventListener("keydown", handleKeyDown);
    return () => {
      scanInput.removeEventListener("keydown", handleKeyDown);
      clearTimeout(scanTimer);
    };
  }, [addToCart, scanning]);

  // ── Totals ──
  const subtotal = cart.reduce((s, c) => s + c.quantity * c.unit_price, 0);
  const taxAmt = subtotal * (parseFloat(taxRate) / 100);
  const discountAmt = parseFloat(discount) || 0;
  const total = subtotal + taxAmt - discountAmt;
  const tendered = parseFloat(amountTendered) || 0;
  const changeDue = tendered > total ? tendered - total : 0;

  // ── PIN gate ──
  if (hasPin === null) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }
  if (!hasPin) {
    // No PIN set — skip gate
  } else if (!pinVerified || locked) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle className="text-center flex items-center justify-center gap-2">
              <Lock className="w-5 h-5" />
              Employee PIN Required
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground text-center mb-4">
              Enter your PIN to access the Point of Sale terminal
            </p>
            <form onSubmit={handlePinSubmit} className="space-y-4">
              <Input
                ref={pinRef}
                type="password"
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="Enter your PIN"
                className="text-center text-2xl tracking-[0.5em] py-6"
                value={pinInput}
                onChange={(e) => {
                  setPinInput(e.target.value.replace(/\D/g, "").slice(0, 10));
                  setPinError("");
                }}
                autoFocus
                disabled={pinVerifying}
              />
              {pinError && (
                <p className="text-sm text-destructive text-center">{pinError}</p>
              )}
              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={pinInput.length < 4 || pinVerifying}
              >
                {pinVerifying ? (
                  <><Loader2 className="w-4 h-4 animate-spin mr-2" />Verifying...</>
                ) : (
                  <><Unlock className="w-4 h-4 mr-2" />Unlock POS</>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Receipt view ──
  if (mode === "receipt" && lastReceipt) {
    const { sale, items } = lastReceipt;
    return (
      <div className="p-4 max-w-2xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Button variant="ghost" size="sm" onClick={() => { setMode("sale"); setLastReceipt(null); }}>
            <ArrowLeft className="w-4 h-4 mr-1" /> New Sale
          </Button>
          <h2 className="text-lg font-bold">Receipt #{sale.receipt_number}</h2>
          {sale.status === "refunded" && <Badge variant="destructive">Refunded</Badge>}
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            <Printer className="w-4 h-4 mr-1" /> Print
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setLocked(true)} title="Lock POS terminal">
            <Lock className="w-4 h-4" />
          </Button>
          <a
            href={`/api/pos/sales/${sale.id}/receipt-pdf`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3"
          >
            <FileDown className="w-4 h-4 mr-1" /> PDF
          </a>
          {sale.status !== "refunded" && sale.status !== "voided" && (
            <Button variant="outline" size="sm" className="text-red-500 border-red-500/30 hover:bg-red-500/10" disabled={refunding} onClick={async () => {
              if (!confirm("Refund this sale? This cannot be undone.")) return;
              setRefunding(true);
              try {
                await api.pos.refund(sale.id);
                setLastReceipt({ ...lastReceipt, sale: { ...sale, status: "refunded", refunded_at: Date.now() } });
                queryClient.invalidateQueries({ queryKey: ["pos-sales"] });
                toast.success("Sale refunded");
              } catch (e) {
                toast.error("Failed to refund");
              } finally {
                setRefunding(false);
              }
            }}>
              <RotateCcw className="w-4 h-4 mr-1" /> {refunding ? "Refunding..." : "Refund"}
            </Button>
          )}
        </div>

        <Card className="print:shadow-none print:border-0">
          <CardContent className="p-6">
            <div className="text-center mb-4 border-b pb-3">
              <h3 className="text-xl font-bold">SpacetimeCRM</h3>
              <p className="text-sm text-muted-foreground">Counter Sale</p>
              <p className="text-xs text-muted-foreground">
                Receipt #{sale.receipt_number} &middot; {new Date(sale.created_at).toLocaleString()}
              </p>
            </div>

            <p className="text-sm mb-3"><span className="text-muted-foreground">Customer:</span> {sale.customer_name}</p>

            <table className="w-full text-sm mb-4">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-1">Item</th>
                  <th className="py-1 text-right">Qty</th>
                  <th className="py-1 text-right">Price</th>
                  <th className="py-1 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-dashed">
                    <td className="py-1">{item.product_name}</td>
                    <td className="py-1 text-right">{item.quantity}</td>
                    <td className="py-1 text-right">${item.unit_price.toFixed(2)}</td>
                    <td className="py-1 text-right font-medium">${item.total.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="space-y-1 text-sm border-t pt-2">
              <div className="flex justify-between">
                <span>Subtotal</span>
                <span>${sale.subtotal.toFixed(2)}</span>
              </div>
              {sale.tax_rate > 0 && (
                <div className="flex justify-between">
                  <span>Tax ({sale.tax_rate}%)</span>
                  <span>${sale.tax_amount.toFixed(2)}</span>
                </div>
              )}
              {sale.discount_amount > 0 && (
                <div className="flex justify-between">
                  <span>Discount</span>
                  <span>-${sale.discount_amount.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between font-bold text-base pt-1 border-t">
                <span>Total</span>
                <span>${sale.total.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Tendered</span>
                <span>${sale.amount_tendered.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-green-600 font-medium">
                <span>Change Due</span>
                <span>${sale.change_due.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-muted-foreground">
                <span>Payment</span>
                <span className="capitalize">{sale.payment_method}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── History mode ──
  if (mode === "history") {
    return (
      <div className="p-4 max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Receipt className="w-5 h-5" /> Sale History
          </h2>
          <Button variant="outline" size="sm" onClick={() => setMode("sale")}>
            <ShoppingCart className="w-4 h-4 mr-1" /> New Sale
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setLocked(true)} title="Lock POS terminal">
            <Lock className="w-4 h-4" />
          </Button>
        </div>

        {loadingHistory ? (
          <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin" /></div>
        ) : (
          <div className="grid gap-3">
            {salesHistory?.map((sale) => (
              <Card key={sale.id} className="hover:bg-accent/50 cursor-pointer" onClick={async () => {
                const detail = await api.pos.get(sale.id);
                setLastReceipt({ sale: detail.sale, items: detail.sale.line_items });
                setMode("receipt");
              }}>
                <CardContent className="p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium flex items-center gap-2">
                      Receipt #{sale.receipt_number}
                      {sale.status === "refunded" && (
                        <Badge variant="destructive" className="text-xs">Refunded</Badge>
                      )}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {sale.customer_name} &middot; {new Date(sale.created_at).toLocaleDateString()}
                    </p>
                    <p className="text-xs text-muted-foreground">{sale.items_count} item(s)</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold">${sale.total.toFixed(2)}</p>
                    <p className="text-xs text-muted-foreground capitalize">{sale.payment_method}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
            {(!salesHistory || salesHistory.length === 0) && (
              <p className="text-center text-muted-foreground py-10">No sales yet</p>
            )}
          </div>
        )}
      </div>
    );
  }

  // ── Sale mode (POS kiosk) ──
  return (
    <div className="p-4 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <ShoppingCart className="w-5 h-5" /> Point of Sale
        </h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setMode("history")}>
            <Receipt className="w-4 h-4 mr-1" /> History
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setLocked(true)} title="Lock POS terminal">
            <Lock className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* ── Left: Product search / scan ── */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Search className="w-4 h-4" /> Scan or Search Products
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
                <Input
                  ref={scanRef}
                  placeholder="Scan barcode or search products..."
                  className="pl-9 text-lg"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  autoFocus
                />
              </div>

              {searchQuery.length >= 1 && searchResults && (
                <div className="mt-2 border rounded-lg divide-y max-h-60 overflow-y-auto">
                  {searchResults.length === 0 ? (
                    <p className="p-3 text-sm text-muted-foreground">No products found</p>
                  ) : (
                    searchResults.slice(0, 10).map((product) => (
                      <div
                        key={product.id}
                        className="flex items-center justify-between p-3 hover:bg-accent cursor-pointer"
                        onClick={() => addToCart(product)}
                      >
                        <div>
                          <p className="font-medium">{product.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {product.sku} &middot; Stock: {product.quantity_on_hand ?? 0}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <p className="font-semibold">${product.price.toFixed(2)}</p>
                          <Button size="icon" variant="ghost" className="w-7 h-7">
                            <Plus className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* ── Quick customer / tender controls ── */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Sale Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="relative">
                  <label className="text-xs text-muted-foreground mb-1 block">Customer</label>
                  <Input
                    value={customerSearch}
                    onChange={(e) => {
                      setCustomerSearch(e.target.value);
                      if (!e.target.value) {
                        setCustomerId("");
                        setCustomerName("Walk-in");
                      }
                    }}
                    placeholder="Search customers..."
                  />
                  {customerSearch.length >= 1 && customerResults && customerResults.length > 0 && (
                    <div className="absolute z-50 top-full left-0 right-0 bg-card border rounded-lg mt-1 shadow-lg max-h-48 overflow-y-auto">
                      {customerResults.map((c) => (
                        <div
                          key={c.id}
                          className="flex items-center justify-between p-2 hover:bg-accent cursor-pointer text-sm"
                          onClick={() => {
                            setCustomerId(c.id);
                            setCustomerName(`${c.first_name} ${c.last_name}`.trim());
                            setCustomerSearch("");
                          }}
                        >
                          <span className="font-medium">{(c.first_name && c.last_name) ? `${c.first_name} ${c.last_name}` : c.email || "Unknown"}</span>
                          <span className="text-xs text-muted-foreground">{c.email || c.phone || ""}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {customerSearch.length > 0 && customerResults && customerResults.length === 0 && (
                    <p className="text-xs text-muted-foreground mt-1">No customers found</p>
                  )}
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Tax Rate %</label>
                  <Input
                    value={taxRate}
                    onChange={(e) => setTaxRate(e.target.value)}
                    type="number"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Discount $</label>
                  <Input
                    value={discount}
                    onChange={(e) => setDiscount(e.target.value)}
                    type="number"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Payment</label>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant={paymentMethod === "cash" ? "default" : "outline"}
                      className="flex-1 text-xs"
                      onClick={() => setPaymentMethod("cash")}
                    >
                      <Banknote className="w-3 h-3 mr-1" /> Cash
                    </Button>
                    <Button
                      size="sm"
                      variant={paymentMethod === "card" ? "default" : "outline"}
                      className="flex-1 text-xs"
                      onClick={() => setPaymentMethod("card")}
                    >
                      <CreditCard className="w-3 h-3 mr-1" /> Card
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* ── Right: Cart / checkout ── */}
        <div className="space-y-4">
          <Card className="h-full flex flex-col">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <ShoppingCart className="w-4 h-4" /> Cart ({cart.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col">
              {/* Cart items */}
              <div className="flex-1 space-y-2 max-h-80 overflow-y-auto mb-3">
                {cart.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    Scan or search products to add
                  </p>
                ) : (
                  cart.map((item) => (
                    <div key={item.product_id} className="flex items-center justify-between border rounded-lg p-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{item.product_name}</p>
                        <p className="text-xs text-muted-foreground">
                          ${item.unit_price.toFixed(2)}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 ml-2">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="w-6 h-6"
                          onClick={() => updateQty(item.product_id, -1)}
                        >
                          <Minus className="w-3 h-3" />
                        </Button>
                        <span className="w-6 text-center text-sm font-medium">{item.quantity}</span>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="w-6 h-6"
                          onClick={() => updateQty(item.product_id, 1)}
                        >
                          <Plus className="w-3 h-3" />
                        </Button>
                      </div>
                      <p className="text-sm font-semibold w-16 text-right">
                        ${(item.quantity * item.unit_price).toFixed(2)}
                      </p>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="w-6 h-6 ml-1 text-red-500"
                        onClick={() => updateQty(item.product_id, -item.quantity)}
                      >
                        <X className="w-3 h-3" />
                      </Button>
                    </div>
                  ))
                )}
              </div>

              {/* Totals */}
              <div className="border-t pt-3 space-y-1 text-sm">
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span>${subtotal.toFixed(2)}</span>
                </div>
                {parseFloat(taxRate) > 0 && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>Tax ({taxRate}%)</span>
                    <span>${taxAmt.toFixed(2)}</span>
                  </div>
                )}
                {discountAmt > 0 && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>Discount</span>
                    <span>-${discountAmt.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between font-bold text-lg pt-1 border-t">
                  <span>Total</span>
                  <span>${total.toFixed(2)}</span>
                </div>
              </div>

              {/* Tendered & change */}
              <div className="mt-3 space-y-2">
                <Input
                  placeholder="Amount tendered"
                  value={amountTendered}
                  onChange={(e) => setAmountTendered(e.target.value)}
                  type="number"
                  step="0.01"
                />
                {tendered > 0 && (
                  <div className="flex justify-between text-sm">
                    <span>Change:</span>
                    <span className={`font-bold ${changeDue > 0 ? "text-green-600" : ""}`}>
                      ${changeDue.toFixed(2)}
                    </span>
                  </div>
                )}
              </div>

              {/* Checkout button */}
              <Button
                className="w-full mt-4"
                size="lg"
                disabled={cart.length === 0 || createMutation.isPending || addItemMutation.isPending}
                onClick={handleSaleComplete}
              >
                {(createMutation.isPending || addItemMutation.isPending) ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                Complete Sale — ${total.toFixed(2)}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
