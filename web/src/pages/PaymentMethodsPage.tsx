import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Customer } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { CreditCard, Plus, Trash2, Star } from "lucide-react";
import { toast } from "sonner";

interface PaymentMethod {
  id: string;
  customer_id: string;
  stripe_payment_method_id: string;
  brand: string;
  last4?: string;
  last_4?: string;
  exp_month: number;
  exp_year: number;
  is_default: boolean;
  created_at: number;
  customer_name?: string;
}

const brandIcons: Record<string, string> = {
  visa: "💳",
  mastercard: "💳",
  amex: "💳",
  discover: "💳",
};

export default function PaymentMethodsPage() {
  const qc = useQueryClient();
  const [customerFilter, setCustomerFilter] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["payment-methods", customerFilter],
    queryFn: async () => {
      const [pmRes, cRes] = await Promise.all([
        api.paymentMethods.list(customerFilter || undefined),
        api.customers.list(),
      ]);
      return { methods: pmRes.payment_methods, customers: cRes.customers };
    },
  });

  const methods = data?.methods ?? [];
  const customers = data?.customers ?? [];

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.paymentMethods.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payment-methods"] });
      toast.success("Payment method removed");
    },
    onError: () => toast.error("Failed to remove payment method"),
  });

  const setDefaultMutation = useMutation({
    mutationFn: ({ id, customer_id }: { id: string; customer_id: string }) =>
      api.paymentMethods.setDefault(id, customer_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payment-methods"] });
      toast.success("Default payment method updated");
    },
    onError: () => toast.error("Failed to set default"),
  });

  const getCustomerName = (customerId: string): string => {
    const c = customers.find((c: Customer) => c.id === customerId);
    return c ? `${c.first_name} ${c.last_name}`.trim() || "—" : "—";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Payment Methods</h1>
          <p className="text-sm text-muted-foreground mt-1">
            View and manage saved customer card details
          </p>
        </div>
      </div>

      {/* Customer filter */}
      <div className="flex gap-2 items-center">
        <label className="text-sm font-medium">Filter by customer:</label>
        <select
          className="border rounded px-3 py-1.5 text-sm bg-background"
          value={customerFilter}
          onChange={(e) => setCustomerFilter(e.target.value)}
        >
          <option value="">All customers</option>
          {customers.map((c: Customer) => (
            <option key={c.id} value={c.id}>
              {c.first_name} {c.last_name}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      ) : methods.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <CreditCard className="h-12 w-12 mx-auto mb-4 opacity-30" />
            <p className="text-lg font-medium">No saved payment methods</p>
            <p className="text-sm mt-1">
              Customers can save cards during portal checkout via Stripe
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {methods.map((pm: PaymentMethod) => (
            <Card key={pm.id}>
              <CardContent className="py-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <CreditCard className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium capitalize">{pm.brand}</span>
                        <span className="font-mono">**** {pm.last_4 || pm.last4 || ""}</span>
                        {pm.is_default && (
                          <Badge variant="success" className="flex items-center gap-1">
                            <Star className="h-3 w-3" /> Default
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Expires {pm.exp_month}/{pm.exp_year}
                        {" · "}
                        {getCustomerName(pm.customer_id)}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-1 shrink-0 ml-4">
                    {!pm.is_default && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          setDefaultMutation.mutate({
                            id: pm.id,
                            customer_id: pm.customer_id,
                          })
                        }
                        title="Set as default"
                      >
                        <Star className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        if (confirm("Remove this payment method?")) {
                          deleteMutation.mutate(pm.id);
                        }
                      }}
                      title="Remove"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
