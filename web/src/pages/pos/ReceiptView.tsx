import { ArrowLeft, Printer, Lock, FileDown, RotateCcw } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Card, CardContent } from "../../components/ui/card";
import { toast } from "sonner";

interface ReceiptViewProps {
  lastReceipt: any;
  setMode: (mode: "sale" | "history" | "receipt") => void;
  setLastReceipt: (data: any) => void;
  setLocked: (locked: boolean) => void;
  refunding: boolean;
  setRefunding: (val: boolean) => void;
  queryClient: any;
}

export default function ReceiptView({
  lastReceipt,
  setMode,
  setLastReceipt,
  setLocked,
  refunding,
  setRefunding,
  queryClient,
}: ReceiptViewProps) {
  const { sale, items } = lastReceipt;

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setMode("sale");
            setLastReceipt(null);
          }}
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> New Sale
        </Button>
        <h2 className="text-lg font-bold">Receipt #{sale.receipt_number}</h2>
        {sale.status === "refunded" && (
          <Badge variant="destructive">Refunded</Badge>
        )}
        <Button variant="outline" size="sm" onClick={() => window.print()}>
          <Printer className="w-4 h-4 mr-1" /> Print
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setLocked(true)}
          title="Lock POS terminal"
        >
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
          <Button
            variant="outline"
            size="sm"
            className="text-red-500 border-red-500/30 hover:bg-red-500/10"
            disabled={refunding}
            onClick={async () => {
              if (!confirm("Refund this sale? This cannot be undone.")) return;
              setRefunding(true);
              try {
                const { api } = await import("../../lib/api");
                await api.pos.refund(sale.id);
                setLastReceipt({
                  ...lastReceipt,
                  sale: {
                    ...sale,
                    status: "refunded",
                    refunded_at: Date.now(),
                  },
                });
                queryClient.invalidateQueries({ queryKey: ["pos-sales"] });
                toast.success("Sale refunded");
              } catch (e) {
                toast.error("Failed to refund");
              } finally {
                setRefunding(false);
              }
            }}
          >
            <RotateCcw className="w-4 h-4 mr-1" />{" "}
            {refunding ? "Refunding..." : "Refund"}
          </Button>
        )}
      </div>

      <Card className="print:shadow-none print:border-0">
        <CardContent className="p-6">
          <div className="text-center mb-4 border-b pb-3">
            <h3 className="text-xl font-bold">SpacetimeCRM</h3>
            <p className="text-sm text-muted-foreground">Counter Sale</p>
            <p className="text-xs text-muted-foreground">
              Receipt #{sale.receipt_number} &middot;{" "}
              {new Date(sale.created_at).toLocaleString()}
            </p>
          </div>

          <p className="text-sm mb-3">
            <span className="text-muted-foreground">Customer:</span>{" "}
            {sale.customer_name}
          </p>

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
              {items.map((item: any) => (
                <tr key={item.id} className="border-b border-dashed">
                  <td className="py-1">{item.product_name}</td>
                  <td className="py-1 text-right">{item.quantity}</td>
                  <td className="py-1 text-right">
                    ${item.unit_price.toFixed(2)}
                  </td>
                  <td className="py-1 text-right font-medium">
                    ${item.total.toFixed(2)}
                  </td>
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
