import { useState, useEffect } from "react";
import { api, Payment, Invoice, Customer } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { CreditCard, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

export default function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ invoice_id: "", customer_id: "", amount: 0, method: "cash", reference: "", notes: "" });

  const load = async () => {
    try {
      const [pRes, iRes, cRes] = await Promise.all([
        api.payments.list(),
        api.invoices.list(),
        api.customers.list(),
      ]);
      setPayments(pRes.payments);
      setInvoices(iRes.invoices);
      setCustomers(cRes.customers);
    } catch { toast.error("Failed to load payments"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleRecord = async () => {
    try {
      await api.payments.record(form);
      toast.success("Payment recorded");
      setShowForm(false);
      setForm({ invoice_id: "", customer_id: "", amount: 0, method: "cash", reference: "", notes: "" });
      load();
    } catch { toast.error("Failed to record payment"); }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.payments.delete(id);
      toast.success("Payment deleted");
      load();
    } catch { toast.error("Failed to delete"); }
  };

  const totalAmount = payments.reduce((sum, p) => sum + p.amount, 0);

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Payments</h1>
          <p className="text-sm text-muted-foreground mt-1">Track payments received</p>
        </div>
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-1.5" />Record Payment</Button>
      </div>

      <Card>
        <CardContent className="pt-4 flex items-center gap-4">
          <CreditCard className="h-8 w-8 text-green-400" />
          <div>
            <p className="text-xs text-muted-foreground">Total Collected</p>
            <p className="text-2xl font-bold text-green-400">${totalAmount.toFixed(2)}</p>
          </div>
        </CardContent>
      </Card>

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader><CardTitle>Record Payment</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Select value={form.invoice_id} onChange={(e) => setForm({ ...form, invoice_id: e.target.value })}>
              <option value="">Select invoice...</option>
              {invoices.map((inv) => (
                <option key={inv.id} value={inv.id}>#{inv.invoice_number} — ${inv.total.toFixed(2)} ({inv.status})</option>
              ))}
            </Select>
            <Select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })}>
              <option value="">Select customer...</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>
              ))}
            </Select>
            <Input type="number" placeholder="Amount" value={form.amount} onChange={(e) => setForm({ ...form, amount: +e.target.value })} />
            <Select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>
              <option value="cash">Cash</option>
              <option value="credit">Credit Card</option>
              <option value="debit">Debit Card</option>
              <option value="check">Check</option>
              <option value="other">Other</option>
            </Select>
            <Input placeholder="Reference" value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
            <Input placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            <div className="flex gap-2">
              <Button onClick={handleRecord}>Record</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {payments.map((p) => (
          <Card key={p.id}>
            <CardContent className="pt-4 flex items-center justify-between">
              <div>
                <p className="font-medium">${p.amount.toFixed(2)}</p>
                <p className="text-xs text-muted-foreground">via {p.method} — {new Date(p.created_at).toLocaleDateString()}</p>
                {p.reference && <p className="text-xs text-muted-foreground">Ref: {p.reference}</p>}
              </div>
              <Button size="icon" variant="ghost" onClick={() => handleDelete(p.id)}><Trash2 className="h-3.5 w-3.5 text-destructive" /></Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
