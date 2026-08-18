import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api } from "../lib/api";
import { usePagination } from "../lib/usePagination";
import { formatCurrency } from "../lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import Pagination from "../components/Pagination";
import { CreditCard, Plus, Trash2, AlertTriangle, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const PAGE_SIZE = 25;

const EMPTY_FORM = { invoice_id: "", customer_id: "", amount: 0, method: "cash", reference: "", notes: "", currency: "USD" };

export default function PaymentsPage() {
  const pag = usePagination(PAGE_SIZE);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["payments", { offset: pag.offset }],
    queryFn: async () => {
      const [pRes, iRes, cRes] = await Promise.all([
        api.payments.list(undefined, pag.offset, PAGE_SIZE),
        api.invoices.list(),
        api.customers.list(),
      ]);
      return { payments: pRes.payments, invoices: iRes.invoices, customers: cRes.customers, total: pRes.total };
    },
  });

  // Sync pagination total outside the query's select to avoid render loops.
  useEffect(() => {
    if (data) pag.setTotal(data.total);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const payments = data?.payments ?? [];
  const invoices = data?.invoices ?? [];
  const customers = data?.customers ?? [];

  const recordMutation = useMutation({
    mutationFn: () => api.payments.record(form),
    onSuccess: () => {
      toast.success("Payment recorded");
      setShowForm(false);
      setForm(EMPTY_FORM);
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

  // Total Collected must be grouped per payment currency — summing amounts
  // across currencies and labeling them with the form's currency was the bug.
  const totalsByCurrency = payments.reduce<Record<string, number>>((acc, p) => {
    const cur = p.currency || "USD";
    acc[cur] = (acc[cur] || 0) + (Number(p.amount) || 0);
    return acc;
  }, {});
  const totalCurrencies = Object.keys(totalsByCurrency).sort();

  return (
    <>
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Payments</h1>
          <p className="text-sm text-muted-foreground mt-1">Track payments received</p>
        </div>
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-1.5" />Record Payment</Button>
      </div>

      {isError && (
        <div className="flex items-center justify-between rounded-lg border border-destructive/30 bg-destructive/10 p-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <p className="text-sm text-destructive">Failed to load payments. Please try again.</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Retry
          </Button>
        </div>
      )}

      <Card>
        <CardContent className="pt-4 flex items-center gap-4">
          <CreditCard className="h-8 w-8 text-green-400" />
          <div className="flex-1">
            <p className="text-xs text-muted-foreground">Total Collected</p>
            {totalCurrencies.length === 0 ? (
              <p className="text-2xl font-bold text-green-400">{formatCurrency(0)}</p>
            ) : (
              <div className="flex flex-wrap gap-x-4">
                {totalCurrencies.map((cur) => (
                  <p key={cur} className="text-2xl font-bold text-green-400">
                    {formatCurrency(totalsByCurrency[cur], cur)}
                    <span className="ml-1.5 text-sm font-medium text-muted-foreground">{cur}</span>
                  </p>
                ))}
              </div>
            )}
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

      <div className="space-y-3">
        {!isLoading && !isError && payments.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              <CreditCard className="h-12 w-12 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium">No payments yet</p>
              <p className="text-sm mt-1">Record your first payment to start tracking revenue</p>
              <Button variant="outline" size="sm" className="mt-4" onClick={() => setShowForm(true)}>
                <Plus className="h-4 w-4 mr-1.5" /> Record Payment
              </Button>
            </CardContent>
          </Card>
        )}
        {payments.map((p) => (
          <Card key={p.id}>
            <CardContent className="pt-4 flex items-center justify-between">
              <div>
                <p className="font-medium">{formatCurrency(p.amount, p.currency)}</p>
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
  );
}
