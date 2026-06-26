import { useState, useEffect } from "react";
import { api, Payment } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { CreditCard, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

export default function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ invoice_id: "", customer_id: "", amount: 0, method: "cash", reference: "", notes: "" });

  const load = async () => {
    try {
      const res = await api.payments.list();
      setPayments(res.payments);
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
            <Input placeholder="Invoice ID" value={form.invoice_id} onChange={(e) => setForm({ ...form, invoice_id: e.target.value })} />
            <Input placeholder="Customer ID" value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} />
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
                <p className="text-xs text-muted-foreground">via {p.method} — {new Date(p.created_at / 1000).toLocaleDateString()}</p>
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
