import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../../lib/query-client";
import { api } from "../../lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Percent, Plus } from "lucide-react";
import { toast } from "sonner";

export default function TaxRateSettings() {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", rate: 0, is_default: false });

  const { data: taxRates = [] } = useQuery({
    queryKey: ["tax-rates"],
    queryFn: async () => {
      const res = await api.taxRates.list();
      return res.tax_rates ?? [];
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; rate: number; is_default: boolean }) =>
      api.taxRates.create(data),
    onSuccess: () => {
      toast.success("Tax rate created");
      setShowForm(false);
      setForm({ name: "", rate: 0, is_default: false });
      queryClient.invalidateQueries({ queryKey: ["tax-rates"] });
    },
    onError: () => {
      toast.error("Failed to create tax rate");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: { name: string; rate: number; is_default: boolean };
    }) => api.taxRates.update(id, data),
    onSuccess: () => {
      toast.success("Default updated");
      queryClient.invalidateQueries({ queryKey: ["tax-rates"] });
    },
    onError: () => {
      toast.error("Failed to update");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.taxRates.delete(id),
    onSuccess: () => {
      toast.success("Tax rate deleted");
      queryClient.invalidateQueries({ queryKey: ["tax-rates"] });
    },
    onError: () => {
      toast.error("Failed to delete");
    },
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Percent className="h-4 w-4" />
          Tax Rates
        </CardTitle>
        <Button size="sm" onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4 mr-1" />
          Add Tax Rate
        </Button>
      </CardHeader>
      <CardContent>
        {showForm && (
          <div className="flex gap-2 mb-4 p-3 rounded bg-muted/50">
            <Input
              placeholder="Name (e.g. Sales Tax)"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <Input
              type="number"
              step="0.01"
              placeholder="Rate %"
              className="w-28"
              value={form.rate || ""}
              onChange={(e) =>
                setForm({ ...form, rate: parseFloat(e.target.value) || 0 })
              }
            />
            <label className="flex items-center gap-1.5 text-sm whitespace-nowrap">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(e) =>
                  setForm({ ...form, is_default: e.target.checked })
                }
                className="rounded border-border"
              />
              Default
            </label>
            <Button size="sm" onClick={() => createMutation.mutate(form)}>
              Save
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
          </div>
        )}
        {taxRates.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No tax rates configured.
          </p>
        ) : (
          <div className="space-y-2">
            {taxRates.map((tr) => (
              <div
                key={tr.id}
                className="flex items-center justify-between py-2"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Percent className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">
                      {tr.name}
                      {tr.is_default && (
                        <Badge variant="success" className="ml-2 text-xs">
                          Default
                        </Badge>
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground">{tr.rate}%</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      updateMutation.mutate({
                        id: tr.id,
                        data: {
                          name: tr.name,
                          rate: tr.rate,
                          is_default: !tr.is_default,
                        },
                      })
                    }
                  >
                    {tr.is_default ? "Unset Default" : "Set Default"}
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => deleteMutation.mutate(tr.id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="border-t pt-3 mt-3">
          <p className="text-xs text-muted-foreground">
            Tax rates are applied to invoices and estimates. The default rate is
            pre-selected when creating new invoices.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
