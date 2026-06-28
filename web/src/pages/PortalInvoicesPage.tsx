import { useState, useEffect } from "react";
import { portalApi, PortalInvoice } from "../lib/portal-auth";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { toast } from "sonner";
import { ChevronDown, ChevronUp, CreditCard, ExternalLink } from "lucide-react";

const statusColors: Record<string, "outline" | "default" | "success" | "destructive"> = {
  draft: "outline",
  sent: "default",
  partial: "default",
  paid: "success",
  overdue: "destructive",
  cancelled: "outline",
};

export default function PortalInvoicesPage() {
  const [invoices, setInvoices] = useState<PortalInvoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<PortalInvoice | null>(null);
  const [payAmount, setPayAmount] = useState(0);
  const [paying, setPaying] = useState(false);
  const [stripeLoading, setStripeLoading] = useState<string | null>(null);

  const load = async () => {
    try {
      const res = await portalApi.invoices.list();
      setInvoices(res.invoices);
    } catch { toast.error("Failed to load invoices"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const toggleDetail = async (id: string) => {
    if (expanded === id) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(id);
    try {
      const res = await portalApi.invoices.get(id);
      setDetail(res.invoice);
      setPayAmount(res.invoice.balance_due ?? res.invoice.total);
    } catch { toast.error("Failed to load invoice"); }
  };

  const handlePayment = async (invoiceId: string) => {
    if (payAmount <= 0) { toast.error("Amount must be > 0"); return; }
    setPaying(true);
    try {
      await portalApi.payments.create(invoiceId, payAmount, "card");
      toast.success("Payment recorded");
      // Reload
      const res = await portalApi.invoices.get(invoiceId);
      setDetail(res.invoice);
    } catch { toast.error("Payment failed"); }
    finally { setPaying(false); }
  };

  const handleStripeCheckout = async (invoiceId: string) => {
    setStripeLoading(invoiceId);
    try {
      const res = await portalApi.payments.createCheckoutSession(invoiceId);
      // Redirect to Stripe Checkout
      window.location.href = res.url;
    } catch (e: any) {
      toast.error(e?.message || "Failed to initiate Stripe payment");
    } finally {
      setStripeLoading(null);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold">My Invoices</h1>
      <p className="text-sm text-muted-foreground mt-1">View and pay your invoices</p>

      <div className="space-y-2 mt-4">
        {invoices.map((inv) => (
          <Card key={inv.id}>
            <CardContent className="pt-4">
              <div className="flex items-start justify-between cursor-pointer" onClick={() => toggleDetail(inv.id)}>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">#{inv.invoice_number}</span>
                    <Badge variant={statusColors[inv.status] || "outline"}>{inv.status}</Badge>
                  </div>
                  <p className="font-medium mt-1">${inv.total.toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground">{new Date(inv.created_at).toLocaleDateString()}</p>
                </div>
                {expanded === inv.id ? <ChevronUp className="h-4 w-4 mt-1" /> : <ChevronDown className="h-4 w-4 mt-1" />}
              </div>

              {expanded === inv.id && detail && (
                <div className="mt-4 border-t pt-4 space-y-3">
                  {/* Line items */}
                  {detail.line_items && detail.line_items.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold mb-2">Items</p>
                      {detail.line_items.map((item) => (
                        <div key={item.id} className="flex justify-between text-sm py-1 border-b border-muted last:border-0">
                          <span>{item.description}</span>
                          <span className="text-muted-foreground">{item.quantity} × ${item.unit_price.toFixed(2)} = ${item.total.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Summary */}
                  <div className="text-sm space-y-1">
                    <div className="flex justify-between"><span className="text-muted-foreground">Subtotal</span><span>${detail.subtotal.toFixed(2)}</span></div>
                    {detail.tax_amount > 0 && <div className="flex justify-between"><span className="text-muted-foreground">Tax</span><span>${detail.tax_amount.toFixed(2)}</span></div>}
                    <div className="flex justify-between font-bold text-base border-t pt-1">
                      <span>Total</span><span>${detail.total.toFixed(2)}</span>
                    </div>
                    {detail.total_paid != null && detail.total_paid > 0 && (
                      <div className="flex justify-between text-green-600">
                        <span>Paid</span><span>-${detail.total_paid.toFixed(2)}</span>
                      </div>
                    )}
                    {detail.balance_due != null && detail.balance_due > 0 && (
                      <div className="flex justify-between font-bold text-red-500">
                        <span>Balance Due</span><span>${detail.balance_due.toFixed(2)}</span>
                      </div>
                    )}
                  </div>

                  {/* Payments history */}
                  {detail.payments && detail.payments.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold mb-1">Payment History</p>
                      {detail.payments.map((p) => (
                        <div key={p.id} className="flex justify-between text-sm py-1">
                          <span className="text-muted-foreground">{p.method} — {new Date(p.created_at).toLocaleDateString()}</span>
                          <span>${p.amount.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Make payment */}
                  {inv.status !== "paid" && inv.status !== "cancelled" && detail.balance_due != null && detail.balance_due > 0 && (
                    <div className="bg-muted/30 rounded p-3 space-y-3">
                      <p className="text-sm font-semibold flex items-center gap-1">
                        <CreditCard className="h-3.5 w-3.5" /> Pay with Card
                      </p>
                      <Button
                        size="sm"
                        className="w-full"
                        onClick={() => handleStripeCheckout(inv.id)}
                        disabled={stripeLoading === inv.id}
                      >
                        {stripeLoading === inv.id ? (
                          "Redirecting to Stripe..."
                        ) : (
                          <>
                            <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                            Pay ${detail.balance_due.toFixed(2)} with Card
                          </>
                        )}
                      </Button>
                      <p className="text-xs text-muted-foreground">
                        Secure payment powered by Stripe
                      </p>

                      <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                          <span className="w-full border-t border-muted" />
                        </div>
                        <div className="relative flex justify-center text-xs">
                          <span className="bg-muted/30 px-2 text-muted-foreground">or pay manually</span>
                        </div>
                      </div>

                      <div className="flex gap-2 items-center">
                        <span className="text-sm">$</span>
                        <Input type="number" className="w-32" step="0.01" min={0.01}
                          value={payAmount} onChange={(e) => setPayAmount(Number(e.target.value))} />
                        <Button size="sm" variant="outline" onClick={() => handlePayment(inv.id)} disabled={paying || payAmount <= 0}>
                          {paying ? "Processing..." : "Record Payment"}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {!loading && invoices.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">No invoices yet</p>
        )}
      </div>
    </div>
  );
}
