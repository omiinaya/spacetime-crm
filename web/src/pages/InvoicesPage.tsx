import { useState, useEffect } from "react";
import { api, Invoice, Customer, InvoiceLineItem } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { FileText, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

const statusColors: Record<string, "default" | "warning" | "success" | "destructive" | "outline"> = {
  draft: "outline",
  sent: "default",
  paid: "success",
  partial: "warning",
  overdue: "destructive",
  cancelled: "outline",
};

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ customer_id: "", ticket_id: "", notes: "", terms: "", due_date: "" });
  const [selectedInv, setSelectedInv] = useState<Invoice | null>(null);
  const [lineItems, setLineItems] = useState<InvoiceLineItem[]>([]);
  const [newItem, setNewItem] = useState({ description: "", quantity: 1, unit_price: 0, item_type: "service" });

  const load = async () => {
    try {
      const [iRes, cRes] = await Promise.all([api.invoices.list(filter), api.customers.list()]);
      setInvoices(iRes.invoices);
      setCustomers(cRes.customers);
    } catch { toast.error("Failed to load invoices"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [filter]);

  const handleCreate = async () => {
    try {
      await api.invoices.create({
        customer_id: form.customer_id,
        ticket_id: form.ticket_id,
        notes: form.notes,
        terms: form.terms,
        due_date: form.due_date ? new Date(form.due_date).getTime() : 0,
      });
      toast.success("Invoice created");
      setShowForm(false);
      setForm({ customer_id: "", ticket_id: "", notes: "", terms: "", due_date: "" });
      load();
    } catch { toast.error("Failed to create invoice"); }
  };

  const selectInvoice = async (inv: Invoice) => {
    setSelectedInv(inv);
    try {
      const res = await api.invoices.lineItems.list(inv.id);
      setLineItems(res.line_items);
    } catch { setLineItems([]); }
    setNewItem({ description: "", quantity: 1, unit_price: 0, item_type: "service" });
  };

  const addLineItem = async () => {
    if (!selectedInv) return;
    try {
      await api.invoices.lineItems.create(selectedInv.id, newItem);
      const res = await api.invoices.lineItems.list(selectedInv.id);
      setLineItems(res.line_items);
      setNewItem({ description: "", quantity: 1, unit_price: 0, item_type: "service" });
      load();
    } catch { toast.error("Failed to add item"); }
  };

  const removeLineItem = async (itemId: string) => {
    if (!selectedInv) return;
    try {
      await api.invoices.lineItems.delete(selectedInv.id, itemId);
      const res = await api.invoices.lineItems.list(selectedInv.id);
      setLineItems(res.line_items);
      load();
    } catch { toast.error("Failed to remove item"); }
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Invoices</h1>
          <p className="text-sm text-muted-foreground mt-1">Billing and invoicing</p>
        </div>
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-1.5" />New Invoice</Button>
      </div>

      <div className="flex gap-2 flex-wrap">
        {["", "draft", "sent", "paid", "overdue", "cancelled"].map((s) => (
          <Button key={s} size="sm" variant={filter === s ? "default" : "outline"} onClick={() => setFilter(s)}>{s || "All"}</Button>
        ))}
      </div>

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
            <div className="flex gap-2">
              <Button onClick={handleCreate}>Create</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-3">
          {invoices.map((inv) => {
            const cust = customers.find((c) => c.id === inv.customer_id);
            return (
              <Card key={inv.id} className={`cursor-pointer transition-colors ${selectedInv?.id === inv.id ? "border-primary" : "hover:border-primary/30"}`} onClick={() => selectInvoice(inv)}>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">#{inv.invoice_number}</span>
                        <Badge variant={statusColors[inv.status] || "outline"}>{inv.status}</Badge>
                      </div>
                      <p className="font-medium mt-1">${inv.total.toFixed(2)}</p>
                      {cust && <p className="text-xs text-muted-foreground">{cust.first_name} {cust.last_name}</p>}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {selectedInv && (
          <div className="space-y-4">
            <Card>
              <CardHeader><CardTitle>#{selectedInv.invoice_number} — ${selectedInv.total.toFixed(2)}</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <Select value={selectedInv.status} onChange={(e) => { api.invoices.updateStatus(selectedInv.id, e.target.value); selectInvoice(selectedInv); }}>
                  <option value="draft">Draft</option>
                  <option value="sent">Sent</option>
                  <option value="paid">Paid</option>
                  <option value="overdue">Overdue</option>
                  <option value="cancelled">Cancelled</option>
                </Select>

                {/* Line items */}
                <div className="space-y-2">
                  {lineItems.map((li) => (
                    <div key={li.id} className="flex items-center justify-between text-sm p-2 rounded bg-muted/50">
                      <div className="min-w-0 flex-1">
                        <p className="truncate">{li.description}</p>
                        <p className="text-xs text-muted-foreground">{li.quantity} x ${li.unit_price.toFixed(2)}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="font-medium">${li.total.toFixed(2)}</span>
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
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </>
  );
}
