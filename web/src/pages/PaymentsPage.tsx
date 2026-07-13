import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api } from "../lib/api";
import { usePagination } from "../lib/usePagination";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import Pagination from "../components/Pagination";
import { CreditCard, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

const PAGE_SIZE = 25;

export default function PaymentsPage() {
  const pag = usePagination(PAGE_SIZE);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ invoice_id: "", customer_id: "", amount: 0, method: "cash", reference: "", notes: "", currency: "USD" });

  const { data, isLoading } = useQuery({
    queryKey: ["payments", { offset: pag.offset }],
    queryFn: async () => {
      const [pRes, iRes, cRes] = await Promise.all([
        api.payments.list(undefined, pag.offset, PAGE_SIZE),
        api.invoices.list(),
        api.customers.list(),
      ]);
      return { payments: pRes.payments, invoices: iRes.invoices, customers: cRes.customers, total: pRes.total };
    },
    select: (res) => {
      pag.setTotal(res.total);
      return { payments: res.payments, invoices: res.invoices, customers: res.customers };
    },
  });

  const payments = data?.payments ?? [];
  const invoices = data?.invoices ?? [];
  const customers = data?.customers ?? [];

  const recordMutation = useMutation({
    mutationFn: () => api.payments.record(form),
    onSuccess: () => {
      toast.success("Payment recorded");
      setShowForm(false);
      setForm({ invoice_id: "", customer_id: "", amount: 0, method: "cash", reference: "", notes: "", currency: "USD" });
      queryClient.invalidateQueries({ queryKey: ["payments"] });
    },
    onError: () => toast.error("Failed to record payment"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.payments.delete(id),
    onSuccess: () => {
      toast.success("Payment deleted");
      queryClient.invalidateQueries({ queryKey: ["payments"] });
    },
    onError: () => toast.error("Failed to delete"),
  });

  const totalsByCurrency = payments.reduce((acc, p) => {
  const ccy = p.currency || "USD";
  acc[ccy] = (acc[ccy] || 0) + p.amount;
  return acc;
}, {} as Record<string, number>);

  return (
    <>
      <div className="flex items-start justify-between gap-2 flex-wrap">
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
            <p className="text-2xl font-bold text-green-400">{Object.entries(totalsByCurrency).map(([ccy, amt]) => `${ccy} ${amt.toFixed(2)}`).join(", ")}</p>
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
                <option key={inv.id} value={inv.id}>#{inv.invoice_number} — {inv.currency || "USD"} {inv.total.toFixed(2)} ({inv.status})</option>
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
            <Select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
              <option value="GBP">GBP (£)</option>
              <option value="CAD">CAD (C$)</option>
              <option value="AUD">AUD (A$)</option>
              <option value="JPY">JPY (¥)</option>
            </Select>
            <div className="flex gap-2">
              <Button onClick={() => recordMutation.mutate()} disabled={recordMutation.isPending}>Record</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {payments.length === 0 ? (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
        <svg className="h-6 w-6 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20 12a8 8 0 11-16 0 8 8 0 0116 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold mb-1">No payments yet</h3>
      <p className="text-sm text-muted-foreground mb-4 max-w-sm">Payments will appear here once recorded</p>
    </div>
  ) : (
    <>
    <div className="space-y-3">
        {payments.map((p) => (
          <Card key={p.id}>
            <CardContent className="pt-4 flex items-center justify-between">
              <div>
                <p className="font-medium">{p.currency || "USD"} {p.amount.toFixed(2)}</p>
                <p className="text-xs text-muted-foreground">via {p.method} — {new Date(p.created_at).toLocaleDateString()}</p>
                {p.reference && <p className="text-xs text-muted-foreground">Ref: {p.reference}</p>}
              </div>
              <Button size="icon" variant="ghost" onClick={() => deleteMutation.mutate(p.id)} disabled={deleteMutation.isPending}><Trash2 className="h-3.5 w-3.5 text-destructive" /></Button>
            </CardContent>
          </Card>
        ))}
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
  )}
</>
  );
}
