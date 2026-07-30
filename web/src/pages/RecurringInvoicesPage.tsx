import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Customer } from "../lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Repeat, Plus, Play, Pause, Trash2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

interface RecurringLineItem {
  description: string;
  quantity: number;
  unit_price: number;
  item_type: string;
}

interface RecurringRule {
  id: string;
  tenant_id: string;
  customer_id: string;
  name: string;
  frequency: string;
  interval_count: number;
  next_generation_date: number;
  last_generated_date: number;
  due_date_days: number;
  line_items_json: string;
  status: string;
  created_at: number;
  updated_at: number;
  customer_name?: string;
}

const frequencies = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Biweekly" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "yearly", label: "Yearly" },
];

const statusColors: Record<string, "success" | "outline" | "destructive"> = {
  active: "success",
  paused: "outline",
  cancelled: "destructive",
};

function tsDate(ts: number): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function parseLineItems(json: string): RecurringLineItem[] {
  try {
    return JSON.parse(json);
  } catch {
    return [];
  }
}

export default function RecurringInvoicesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editRule, setEditRule] = useState<RecurringRule | null>(null);
  const [form, setForm] = useState({
    customer_id: "",
    name: "",
    frequency: "monthly",
    interval_count: 1,
    due_date_days: 30,
    next_generation_date: "",
  });
  const [lineItems, setLineItems] = useState<RecurringLineItem[]>([
    { description: "", quantity: 1, unit_price: 0, item_type: "service" },
  ]);

  const { data, isLoading } = useQuery({
    queryKey: ["recurring-invoices"],
    queryFn: async () => {
      const [rRes, cRes] = await Promise.all([
        api.recurringInvoices.list(),
        api.customers.list(),
      ]);
      return { rules: rRes.rules, customers: cRes.customers };
    },
  });

  const rules = data?.rules ?? [];
  const customers = data?.customers ?? [];

  const resetForm = () => {
    setForm({
      customer_id: "",
      name: "",
      frequency: "monthly",
      interval_count: 1,
      due_date_days: 30,
      next_generation_date: "",
    });
    setLineItems([
      { description: "", quantity: 1, unit_price: 0, item_type: "service" },
    ]);
    setShowForm(false);
    setEditRule(null);
  };

  const createMutation = useMutation({
    mutationFn: () =>
      api.recurringInvoices.create({
        customer_id: form.customer_id,
        name: form.name,
        frequency: form.frequency,
        interval_count: form.interval_count,
        due_date_days: form.due_date_days,
        next_generation_date: form.next_generation_date
          ? new Date(form.next_generation_date).getTime()
          : 0,
        line_items: lineItems.filter((li) => li.description.trim()),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["recurring-invoices"] });
      toast.success("Recurring rule created");
      resetForm();
    },
    onError: () => toast.error("Failed to create rule"),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      ...data
    }: { id: string } & Parameters<typeof api.recurringInvoices.update>[1]) =>
      api.recurringInvoices.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["recurring-invoices"] });
      toast.success("Rule updated");
      resetForm();
    },
    onError: () => toast.error("Failed to update rule"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.recurringInvoices.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["recurring-invoices"] });
      toast.success("Rule deleted");
    },
    onError: () => toast.error("Failed to delete rule"),
  });

  const generateMutation = useMutation({
    mutationFn: () => api.recurringInvoices.generate(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["recurring-invoices"] });
      toast.success("Invoices generated!");
    },
    onError: () => toast.error("Generation failed"),
  });

  const handleEdit = (rule: RecurringRule) => {
    setEditRule(rule);
    setForm({
      customer_id: rule.customer_id,
      name: rule.name,
      frequency: rule.frequency,
      interval_count: rule.interval_count,
      due_date_days: rule.due_date_days,
      next_generation_date: rule.next_generation_date
        ? new Date(rule.next_generation_date).toISOString().slice(0, 10)
        : "",
    });
    setLineItems(parseLineItems(rule.line_items_json));
    if (parseLineItems(rule.line_items_json).length === 0) {
      setLineItems([
        { description: "", quantity: 1, unit_price: 0, item_type: "service" },
      ]);
    }
    setShowForm(true);
  };

  const handleSave = () => {
    const data = {
      name: form.name,
      frequency: form.frequency,
      interval_count: form.interval_count,
      due_date_days: form.due_date_days,
      next_generation_date: form.next_generation_date
        ? new Date(form.next_generation_date).getTime()
        : 0,
      line_items: lineItems.filter((li) => li.description.trim()),
      status: editRule?.status ?? "active",
    };
    if (editRule) {
      updateMutation.mutate({ id: editRule.id, ...data });
    } else {
      createMutation.mutate();
    }
  };

  const toggleStatus = (rule: RecurringRule) => {
    const newStatus = rule.status === "active" ? "paused" : "active";
    const li = parseLineItems(rule.line_items_json);
    updateMutation.mutate({
      id: rule.id,
      name: rule.name,
      frequency: rule.frequency,
      interval_count: rule.interval_count,
      due_date_days: rule.due_date_days,
      next_generation_date: rule.next_generation_date,
      line_items: li,
      status: newStatus,
    });
  };

  const addLineItem = () => {
    setLineItems([
      ...lineItems,
      { description: "", quantity: 1, unit_price: 0, item_type: "service" },
    ]);
  };

  const updateLineItem = (
    idx: number,
    field: keyof RecurringLineItem,
    value: string | number,
  ) => {
    const updated = [...lineItems];
    (updated[idx] as any)[field] = value;
    setLineItems(updated);
  };

  const removeLineItem = (idx: number) => {
    if (lineItems.length > 1) {
      setLineItems(lineItems.filter((_, i) => i !== idx));
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Recurring Invoices</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Automatically generate invoices on a schedule
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${generateMutation.isPending ? "animate-spin" : ""}`}
            />
            Generate Now
          </Button>
          <Button
            onClick={() => {
              resetForm();
              setShowForm(!showForm);
            }}
          >
            <Plus className="h-4 w-4 mr-2" />
            New Rule
          </Button>
        </div>
      </div>

      {/* Form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {editRule ? "Edit Rule" : "Create Recurring Invoice Rule"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Customer *
                </label>
                <Select
                  value={form.customer_id}
                  onChange={(e) =>
                    setForm({ ...form, customer_id: e.target.value })
                  }
                >
                  <option value="">Select customer...</option>
                  {customers.map((c: Customer) => (
                    <option key={c.id} value={c.id}>
                      {c.first_name} {c.last_name}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Rule Name *
                </label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Monthly Maintenance"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Frequency
                </label>
                <Select
                  value={form.frequency}
                  onChange={(e) =>
                    setForm({ ...form, frequency: e.target.value })
                  }
                >
                  {frequencies.map((f) => (
                    <option key={f.value} value={f.value}>
                      {f.label}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Every (interval)
                </label>
                <Input
                  type="number"
                  min={1}
                  value={form.interval_count}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      interval_count: parseInt(e.target.value) || 1,
                    })
                  }
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Due Date (days after)
                </label>
                <Input
                  type="number"
                  min={0}
                  value={form.due_date_days}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      due_date_days: parseInt(e.target.value) || 0,
                    })
                  }
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  First Generation Date
                </label>
                <Input
                  type="date"
                  value={form.next_generation_date}
                  onChange={(e) =>
                    setForm({ ...form, next_generation_date: e.target.value })
                  }
                />
              </div>
            </div>

            {/* Line items */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">
                  Line Items (template)
                </label>
                <Button variant="ghost" size="sm" onClick={addLineItem}>
                  <Plus className="h-3 w-3 mr-1" /> Add Item
                </Button>
              </div>
              <div className="space-y-2">
                {lineItems.map((li, idx) => (
                  <div key={idx} className="flex gap-2 items-start">
                    <Input
                      placeholder="Description"
                      value={li.description}
                      onChange={(e) =>
                        updateLineItem(idx, "description", e.target.value)
                      }
                      className="flex-1"
                    />
                    <Input
                      type="number"
                      placeholder="Qty"
                      value={li.quantity}
                      onChange={(e) =>
                        updateLineItem(
                          idx,
                          "quantity",
                          parseFloat(e.target.value) || 0,
                        )
                      }
                      className="w-20"
                    />
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="Price"
                      value={li.unit_price}
                      onChange={(e) =>
                        updateLineItem(
                          idx,
                          "unit_price",
                          parseFloat(e.target.value) || 0,
                        )
                      }
                      className="w-24"
                    />
                    {lineItems.length > 1 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeLineItem(idx)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={resetForm}>
                Cancel
              </Button>
              <Button onClick={handleSave}>
                {editRule ? "Update Rule" : "Create Rule"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Rules list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      ) : rules.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Repeat className="h-12 w-12 mx-auto mb-4 opacity-30" />
            <p className="text-lg font-medium">
              No recurring invoice rules yet
            </p>
            <p className="text-sm mt-1">
              Create your first rule to automate invoice generation
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {rules.map((rule: RecurringRule) => {
            const items = parseLineItems(rule.line_items_json);
            const total = items.reduce(
              (s, i) => s + i.quantity * i.unit_price,
              0,
            );
            return (
              <Card key={rule.id}>
                <CardContent className="py-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Repeat className="h-4 w-4 text-primary" />
                        <span className="font-medium">{rule.name}</span>
                        <Badge variant={statusColors[rule.status] || "outline"}>
                          {rule.status}
                        </Badge>
                      </div>
                      <div className="mt-1 text-sm text-muted-foreground space-y-0.5">
                        <p>
                          Customer:{" "}
                          <span className="text-foreground">
                            {rule.customer_name || "—"}
                          </span>
                          {" · "}
                          Frequency:{" "}
                          <span className="text-foreground capitalize">
                            {rule.frequency}
                          </span>
                          {rule.interval_count > 1 &&
                            ` (×${rule.interval_count})`}
                        </p>
                        <p>
                          Next:{" "}
                          <span className="text-foreground">
                            {tsDate(rule.next_generation_date)}
                          </span>
                          {" · "}
                          Last:{" "}
                          <span className="text-foreground">
                            {tsDate(rule.last_generated_date)}
                          </span>
                          {" · "}
                          Due:{" "}
                          {rule.due_date_days > 0
                            ? `${rule.due_date_days}d after`
                            : "upon creation"}
                        </p>
                        {items.length > 0 && (
                          <p className="text-xs mt-1">
                            {items.length} line item
                            {items.length !== 1 ? "s" : ""}
                            {total > 0 && ` (≈ $${total.toFixed(2)})`}
                            {items.map((i, idx) => (
                              <span
                                key={idx}
                                className="block ml-4 text-muted-foreground/70"
                              >
                                · {i.description || "(no description)"} —{" "}
                                {i.quantity} × ${i.unit_price.toFixed(2)}
                              </span>
                            ))}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-1 shrink-0 ml-4">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => toggleStatus(rule)}
                        title={rule.status === "active" ? "Pause" : "Resume"}
                      >
                        {rule.status === "active" ? (
                          <Pause className="h-4 w-4" />
                        ) : (
                          <Play className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleEdit(rule)}
                        title="Edit"
                      >
                        <svg
                          className="h-4 w-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          />
                        </svg>
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          if (confirm("Delete this recurring rule?")) {
                            deleteMutation.mutate(rule.id);
                          }
                        }}
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
