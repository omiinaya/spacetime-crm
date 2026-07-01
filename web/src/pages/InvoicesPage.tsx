import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api, Invoice, Customer, TaxRate, Payment, InvoiceSummary } from "../lib/api";
import { usePagination } from "../lib/usePagination";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import Pagination from "../components/Pagination";
import { FileText, Plus, Trash2, FileDown, DollarSign, CreditCard, CheckSquare, Square } from "lucide-react";
import { toast } from "sonner";

const PAGE_SIZE = 25;

const statusColors: Record<string, "default" | "warning" | "success" | "destructive" | "outline"> = {
  draft: "outline",
  sent: "default",
  paid: "success",
  partial: "warning",
  overdue: "destructive",
  cancelled: "outline",
};

export default function InvoicesPage() {
  const pag = usePagination(PAGE_SIZE);
  const [filter, setFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ customer_id: "", ticket_id: "", notes: "", terms: "", due_date: "", currency: "USD" });
  const [selectedInv, setSelectedInv] = useState<Invoice | null>(null);
  const [showPaymentForm, setShowPaymentForm] = useState(false);
  const [paymentForm, setPaymentForm] = useState({ amount: 0, method: "cash", reference: "" });
  const [newItem, setNewItem] = useState({ description: "", quantity: 1, unit_price: 0, item_type: "service" });
  const [taxRates, setTaxRates] = useState<TaxRate[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkStatus, setBulkStatus] = useState("sent");

  const { data: summary } = useQuery({
    queryKey: ["invoice-summary"],
    queryFn: () => api.invoices.summary(),
  });

  const bulkMutation = useMutation({
    mutationFn: () => api.invoices.bulkStatusUpdate(Array.from(selectedIds), bulkStatus),
    onSuccess: (data) => {
      toast.success(`Updated ${data.updated} invoice(s) to ${bulkStatus}`);
      setSelectedIds(new Set());
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      queryClient.invalidateQueries({ queryKey: ["invoice-summary"] });
    },
    onError: () => toast.error("Bulk update failed"),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["invoices", { filter, offset: pag.offset }],
    queryFn: async () => {
      const [iRes, cRes, tRes] = await Promise.all([
        api.invoices.list(filter, pag.offset, PAGE_SIZE),
        api.customers.list(),
        api.taxRates.list(),
      ]);
      return { invoices: iRes.invoices, customers: cRes.customers, tax_rates: tRes.tax_rates, total: iRes.total };
    },
    select: (res) => {
      pag.setTotal(res.total);
      setTaxRates(res.tax_rates);
      return { invoices: res.invoices, customers: res.customers };
    },
  });

  const invoices = data?.invoices ?? [];
  const customers = data?.customers ?? [];

  const createMutation = useMutation({
    mutationFn: () => api.invoices.create({
      customer_id: form.customer_id,
      ticket_id: form.ticket_id,
      notes: form.notes,
      terms: form.terms,
      due_date: form.due_date ? new Date(form.due_date).getTime() : 0,
      currency: form.currency,
    }),
    onSuccess: () => {
      toast.success("Invoice created");
      setShowForm(false);
      setForm({ customer_id: "", ticket_id: "", notes: "", terms: "", due_date: "", currency: "USD" });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: () => toast.error("Failed to create invoice"),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.invoices.updateStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      queryClient.invalidateQueries({ queryKey: ["invoice-line-items"] });
    },
  });

  const taxMutation = useMutation({
    mutationFn: ({ id, rate }: { id: string; rate: number }) => api.taxRates.setInvoiceTaxRate(id, rate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      queryClient.invalidateQueries({ queryKey: ["invoice-line-items"] });
    },
  });

  const lineItemMutation = useMutation({
    mutationFn: (item: { description: string; quantity: number; unit_price: number; item_type: string }) =>
      api.invoices.lineItems.create(selectedInv!.id, item),
    onSuccess: () => {
      setNewItem({ description: "", quantity: 1, unit_price: 0, item_type: "service" });
      queryClient.invalidateQueries({ queryKey: ["invoice-line-items", selectedInv?.id] });
    },
    onError: () => toast.error("Failed to add item"),
  });

  const removeLineItemMutation = useMutation({
    mutationFn: (itemId: string) => api.invoices.lineItems.delete(selectedInv!.id, itemId),
    onSuccess: (_, itemId) => {
      queryClient.invalidateQueries({ queryKey: ["invoice-line-items", selectedInv?.id] });
    },
    onError: () => toast.error("Failed to remove item"),
  });

  const recordPaymentMutation = useMutation({
    mutationFn: () => {
      if (!selectedInv) throw new Error("No invoice selected");
      const cust = customers.find(c => c.id === selectedInv.customer_id);
      return api.payments.record({
        invoice_id: selectedInv.id,
        customer_id: selectedInv.customer_id,
        amount: paymentForm.amount || selectedInv.total,
        method: paymentForm.method,
        reference: paymentForm.reference,
        notes: "",
        currency: selectedInv.currency || "USD",
      });
    },
    onSuccess: () => {
      toast.success("Payment recorded");
      setShowPaymentForm(false);
      setPaymentForm({ amount: 0, method: "cash", reference: "" });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: () => toast.error("Failed to record payment"),
  });

  const { data: lineItemsData } = useQuery({
    queryKey: ["invoice-line-items", selectedInv?.id],
    queryFn: async () => {
      const res = await api.invoices.lineItems.list(selectedInv!.id);
      return res.line_items;
    },
    enabled: !!selectedInv,
  });

  const handleFilter = (val: string) => {
    setFilter(val);
    pag.reset();
  };

  const selectInvoice = async (inv: Invoice) => {
    setSelectedInv(inv);
    setNewItem({ description: "", quantity: 1, unit_price: 0, item_type: "service" });
  };

  const lineItems = lineItemsData ?? [];

  const addLineItem = () => {
    if (!selectedInv) return;
    lineItemMutation.mutate(newItem);
  };

  const removeLineItem = (itemId: string) => {
    if (!selectedInv) return;
    removeLineItemMutation.mutate(itemId);
  };

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === invoices.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(invoices.map(i => i.id)));
    }
  };

  return (
    <>
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Invoices</h1>
          <p className="text-sm text-muted-foreground mt-1">Billing and invoicing</p>
        </div>
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-1.5" />New Invoice</Button>
      </div>

      <div className="flex gap-2 flex-wrap">
        {["", "draft", "sent", "paid", "overdue", "cancelled"].map((s) => (
          <Button key={s} size="sm" variant={filter === s ? "default" : "outline"} onClick={() => handleFilter(s)}>{s || "All"}</Button>
        ))}
      </div>

      {/* Summary bar */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="border rounded-lg p-3">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="text-lg font-bold">{summary.total_count}</p>
          </div>
          <div className="border rounded-lg p-3">
            <p className="text-xs text-muted-foreground">Outstanding</p>
            <p className="text-lg font-bold text-amber-400">${summary.total_outstanding.toFixed(2)}</p>
          </div>
          <div className="border rounded-lg p-3">
            <p className="text-xs text-muted-foreground">Overdue</p>
            <p className="text-lg font-bold text-red-400">{summary.overdue_count} / ${summary.overdue_total.toFixed(2)}</p>
          </div>
          <div className="border rounded-lg p-3">
            <p className="text-xs text-muted-foreground">Revenue</p>
            <p className="text-lg font-bold text-green-400">${summary.total_revenue.toFixed(2)}</p>
          </div>
        </div>
      )}

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-2 p-3 rounded-lg border border-primary/30 bg-primary/5">
          <span className="text-sm font-medium">{selectedIds.size} selected</span>
          <div className="flex-1" />
          <Select value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value)} className="w-28">
            <option value="draft">Draft</option>
            <option value="sent">Sent</option>
            <option value="paid">Paid</option>
            <option value="overdue">Overdue</option>
            <option value="cancelled">Cancelled</option>
          </Select>
          <Button
            size="sm"
            onClick={() => bulkMutation.mutate()}
            disabled={bulkMutation.isPending}
          >
            {bulkMutation.isPending ? (
              <span className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full mr-1" />
            ) : null}
            Apply
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())}>
            Clear
          </Button>
        </div>
      )}

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader><CardTitle>New Invoice</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })}>
              <option value="">Select customer...</option>
              {customers.map((c) => (<option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>))}
            </Select>
            <Input placeholder="Ticket ID (optional)" value={form.ticket_id} onChange={(e) => setForm({ ...form, ticket_id: e.target.value })} />
            <Input placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            <Input placeholder="Terms" value={form.terms} onChange={(e) => setForm({ ...form, terms: e.target.value })} />
            <Input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
            <Select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
              <option value="GBP">GBP (£)</option>
              <option value="CAD">CAD (C$)</option>
              <option value="AUD">AUD (A$)</option>
              <option value="JPY">JPY (¥)</option>
            </Select>
            <div className="flex gap-2">
              <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>Create</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={`space-y-3 ${selectedInv ? "hidden lg:block" : ""}`}>
          {/* Select all header */}
          {invoices.length > 0 && (
            <div className="flex items-center gap-2 px-1 pb-1 text-xs text-muted-foreground">
              <button onClick={toggleSelectAll} className="flex items-center gap-1.5 hover:text-foreground">
                {selectedIds.size === invoices.length ? <CheckSquare className="h-3.5 w-3.5" /> : <Square className="h-3.5 w-3.5" />}
                {selectedIds.size === invoices.length ? "Deselect all" : "Select all"}
              </button>
              {selectedIds.size > 0 && <span className="text-primary font-medium">{selectedIds.size} selected</span>}
            </div>
          )}
          {invoices.map((inv) => {
            const cust = customers.find((c) => c.id === inv.customer_id);
            return (
              <div key={inv.id} className="flex items-start gap-2">
                <button onClick={(e) => { e.stopPropagation(); toggleSelect(inv.id); }} className="mt-4 shrink-0 hover:text-foreground text-muted-foreground">
                  {selectedIds.has(inv.id) ? <CheckSquare className="h-4 w-4" /> : <Square className="h-4 w-4" />}
                </button>
                <Card className={`flex-1 cursor-pointer transition-colors ${selectedInv?.id === inv.id ? "border-primary" : "hover:border-primary/30"}`} onClick={() => selectInvoice(inv)}>
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">#{inv.invoice_number}</span>
                          <Badge variant={statusColors[inv.status] || "outline"}>{inv.status}</Badge>
                        </div>
                        <p className="font-medium mt-1">{inv.currency || "USD"} {inv.total.toFixed(2)}</p>
                        {cust && <p className="text-xs text-muted-foreground">{cust.first_name} {cust.last_name}</p>}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>

        {selectedInv && (
          <div className="space-y-4">
            {/* Back button (mobile) */}
            <button
              onClick={() => setSelectedInv(null)}
              className="lg:hidden text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              ← Back to list
            </button>
            <Card>
              <CardHeader><CardTitle>#{selectedInv.invoice_number} — {selectedInv.currency || "USD"} {selectedInv.total.toFixed(2)}</CardTitle>
                <Button size="sm" variant="outline" onClick={() => window.open(`/api/invoices/${selectedInv.id}/pdf`, "_blank")}>
                  <FileDown className="h-3.5 w-3.5 mr-1" /> PDF
                </Button>
              </CardHeader>
              <CardContent className="space-y-3">
                <Select value={selectedInv.status} onChange={(e) => statusMutation.mutate({ id: selectedInv.id, status: e.target.value })}>
                  <option value="draft">Draft</option>
                  <option value="sent">Sent</option>
                  <option value="paid">Paid</option>
                  <option value="overdue">Overdue</option>
                  <option value="cancelled">Cancelled</option>
                </Select>

                {/* Tax rate selector */}
                <div className="flex items-center gap-2">
                  <label className="text-xs text-muted-foreground whitespace-nowrap">Tax Rate:</label>
                  <Select
                    value={String(selectedInv.tax_rate)}
                    onChange={(e) => taxMutation.mutate({ id: selectedInv.id, rate: parseFloat(e.target.value) })}
                    className="flex-1"
                  >
                    <option value="0">No tax</option>
                    {taxRates.map((tr) => (
                      <option key={tr.id} value={tr.rate}>{tr.name} ({tr.rate}%)</option>
                    ))}
                  </Select>
                  <span className="text-sm font-medium tabular-nums">
                    {selectedInv.currency || "USD"} {((selectedInv.subtotal * (selectedInv.tax_rate || 0) / 100)).toFixed(2)}
                  </span>
                </div>

                {/* Line items */}
                <div className="space-y-2">
                  {lineItems.map((li) => (
                    <div key={li.id} className="flex items-center justify-between text-sm p-2 rounded bg-muted/50">
                      <div className="min-w-0 flex-1">
                        <p className="truncate">{li.description}</p>
                        <p className="text-xs text-muted-foreground">{li.quantity} x {selectedInv.currency || "USD"} {li.unit_price.toFixed(2)}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="font-medium">{selectedInv.currency || "USD"} {li.total.toFixed(2)}</span>
                        <Button size="icon" variant="ghost" onClick={() => removeLineItem(li.id)}><Trash2 className="h-3 w-3" /></Button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-2">
                  <Select value={newItem.item_type} onChange={(e) => setNewItem({ ...newItem, item_type: e.target.value })} className="w-28">
                    <option value="service">Service</option>
                    <option value="part">Part</option>
                  </Select>
                  <Input placeholder="Description" value={newItem.description} onChange={(e) => setNewItem({ ...newItem, description: e.target.value })} />
                  <Input type="number" placeholder="Qty" value={newItem.quantity} onChange={(e) => setNewItem({ ...newItem, quantity: +e.target.value })} className="w-20" />
                  <Input type="number" placeholder="Price" value={newItem.unit_price} onChange={(e) => setNewItem({ ...newItem, unit_price: +e.target.value })} className="w-24" />
                  <Button size="sm" onClick={addLineItem}><Plus className="h-3 w-3" /></Button>
                </div>

                {/* Record Payment */}
                <div className="border-t border-border pt-3 mt-2">
                  {!showPaymentForm ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full gap-2"
                      onClick={() => setShowPaymentForm(true)}
                    >
                      <DollarSign className="h-4 w-4" />
                      Record Payment
                    </Button>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-sm font-medium flex items-center gap-2">
                        <DollarSign className="h-4 w-4" />
                        Record Payment
                      </p>
                      <div className="flex items-center gap-2">
                        <Input
                          type="number"
                          placeholder="Amount"
                          value={paymentForm.amount || selectedInv.total}
                          onChange={(e) => setPaymentForm({ ...paymentForm, amount: parseFloat(e.target.value) || 0 })}
                          className="w-28"
                        />
                        <Select
                          value={paymentForm.method}
                          onChange={(e) => setPaymentForm({ ...paymentForm, method: e.target.value })}
                          className="flex-1"
                        >
                          <option value="cash">Cash</option>
                          <option value="card">Card</option>
                          <option value="check">Check</option>
                          <option value="stripe">Stripe</option>
                          <option value="other">Other</option>
                        </Select>
                      </div>
                      <div className="flex items-center gap-2">
                        <Input
                          placeholder="Reference (optional)"
                          value={paymentForm.reference}
                          onChange={(e) => setPaymentForm({ ...paymentForm, reference: e.target.value })}
                          className="flex-1"
                        />
                        <Button
                          size="sm"
                          onClick={() => recordPaymentMutation.mutate()}
                          disabled={recordPaymentMutation.isPending}
                        >
                          {recordPaymentMutation.isPending ? (
                            <span className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full" />
                          ) : (
                            <CreditCard className="h-3.5 w-3.5" />
                          )}
                          Pay
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setShowPaymentForm(false)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
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
