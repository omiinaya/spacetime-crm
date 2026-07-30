import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Select } from "../../components/ui/select";
import type { UseMutationResult } from "@tanstack/react-query";

interface InvoicePaymentFormProps {
  showPaymentForm: boolean;
  setShowPaymentForm: (v: boolean) => void;
  paymentForm: { amount: number; method: string; reference: string };
  setPaymentForm: (f: {
    amount: number;
    method: string;
    reference: string;
  }) => void;
  recordPaymentMutation: UseMutationResult<
    { ok: boolean },
    Error,
    void,
    unknown
  >;
  selectedInvTotal: number;
}

export default function InvoicePaymentForm({
  showPaymentForm,
  setShowPaymentForm,
  paymentForm,
  setPaymentForm,
  recordPaymentMutation,
  selectedInvTotal,
}: InvoicePaymentFormProps) {
  if (!showPaymentForm) {
    return (
      <Button
        variant="outline"
        size="sm"
        className="w-full gap-2"
        onClick={() => setShowPaymentForm(true)}
      >
        <span className="h-4 w-4">💰</span>
        Record Payment
      </Button>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium flex items-center gap-2">
        <span className="h-4 w-4">💰</span>
        Record Payment
      </p>
      <div className="flex items-center gap-2">
        <Input
          type="number"
          placeholder="Amount"
          value={paymentForm.amount || selectedInvTotal}
          onChange={(e) =>
            setPaymentForm({
              ...paymentForm,
              amount: parseFloat(e.target.value) || 0,
            })
          }
          className="w-28"
        />
        <Select
          value={paymentForm.method}
          onChange={(e) =>
            setPaymentForm({
              ...paymentForm,
              method: e.target.value,
            })
          }
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
          onChange={(e) =>
            setPaymentForm({
              ...paymentForm,
              reference: e.target.value,
            })
          }
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
            <span className="h-3.5 w-3.5">💳</span>
          )}
          Pay
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setShowPaymentForm(false)}
        >
          Cancel
        </Button>
      </div>
    </div>
  );
}
