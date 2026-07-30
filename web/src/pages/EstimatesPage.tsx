import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api, Estimate, Customer, EstimateLineItem } from "../lib/api";
import { usePagination } from "../lib/usePagination";
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
import Pagination from "../components/Pagination";
import { FileCheck, Plus, Trash2, FileText } from "lucide-react";

const PAGE_SIZE = 25;
import { toast } from "sonner";

const statusColors: Record<
  string,
  "default" | "warning" | "success" | "destructive" | "outline"
> = {
  draft: "outline",
  sent: "default",
  approved: "success",
  declined: "destructive",
};

export default function EstimatesPage() {
  const pag = usePagination(PAGE_SIZE);
  const [filter, setFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    customer_id: "",
    ticket_id: "",
    notes: "",
    expires_at: "",
    currency: "USD",
  });
  const [selectedEst, setSelectedEst] = useState<Estimate | null>(null);
  const [newItem, setNewItem] = useState({
    description: "",
    quantity: 1,
    unit_price: 0,
    item_type: "service",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["estimates", { filter, offset: pag.offset }],
    queryFn: async () => {
      const [eRes, cRes] = await Promise.all([
        api.estimates.list(filter, pag.offset, PAGE_SIZE),
        api.customers.list(),
      ]);
      return {
        estimates: eRes.estimates,
        customers: cRes.customers,
        total: eRes.total,
      };
    },
    select: (res) => {
      pag.setTotal(res.total);
      return { estimates: res.estimates, customers: res.customers };
    },
  });

  const estimates = data?.estimates ?? [];
  const customers = data?.customers ?? [];

  const { data: lineItemsData } = useQuery({
    queryKey: ["estimate-line-items", selectedEst?.id],
    queryFn: async () => {
      if (!selectedEst) return [];
      const res = await api.estimates.lineItems.list(selectedEst.id);
      return res.line_items;
    },
    enabled: !!selectedEst,
  });

  const lineItems = lineItemsData ?? [];

  const createMutation = useMutation({
    mutationFn: () =>
      api.estimates.create({
        customer_id: form.customer_id,
        ticket_id: form.ticket_id,
        notes: form.notes,
        expires_at: form.expires_at ? new Date(form.expires_at).getTime() : 0,
        currency: form.currency,
      }),
    onSuccess: () => {
      toast.success("Estimate created");
      setShowForm(false);
      setForm({
        customer_id: "",
        ticket_id: "",
        notes: "",
        expires_at: "",
        currency: "USD",
      });
      queryClient.invalidateQueries({ queryKey: ["estimates"] });
    },
    onError: () => toast.error("Failed to create estimate"),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.estimates.updateStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["estimates"] });
    },
  });

  const convertMutation = useMutation({
    mutationFn: (id: string) => api.estimates.convert(id),
    onSuccess: () => {
      toast.success("Converted to invoice!");
      setSelectedEst(null);
      queryClient.invalidateQueries({ queryKey: ["estimates"] });
    },
    onError: () => toast.error("Failed to convert"),
  });

  const lineItemMutation = useMutation({
    mutationFn: (item: {
      description: string;
      quantity: number;
      unit_price: number;
      item_type: string;
    }) => api.estimates.lineItems.create(selectedEst!.id, item),
    onSuccess: () => {
      setNewItem({
        description: "",
        quantity: 1,
        unit_price: 0,
        item_type: "service",
      });
      queryClient.invalidateQueries({
        queryKey: ["estimate-line-items", selectedEst?.id],
      });
      queryClient.invalidateQueries({ queryKey: ["estimates"] });
    },
    onError: () => toast.error("Failed to add item"),
  });

  const selectEst = (est: Estimate) => {
    setSelectedEst(est);
    setNewItem({
      description: "",
      quantity: 1,
      unit_price: 0,
      item_type: "service",
    });
  };

  const handleCreate = () => {
    createMutation.mutate();
  };

  const addLineItem = () => {
    if (!selectedEst) return;
    lineItemMutation.mutate(newItem);
  };

  return (
    <>
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Estimates</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create and manage estimates
          </p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4 mr-1.5" />
          New Estimate
        </Button>
      </div>

      <div className="flex gap-2 flex-wrap">
        {["", "draft", "sent", "approved", "declined"].map((s) => (
          <Button
            key={s}
            size="sm"
            variant={filter === s ? "default" : "outline"}
            onClick={() => {
              setFilter(s);
              pag.reset();
            }}
          >
            {s || "All"}
          </Button>
        ))}
      </div>

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader>
            <CardTitle>New Estimate</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select
              value={form.customer_id}
              onChange={(e) =>
                setForm({ ...form, customer_id: e.target.value })
              }
            >
              <option value="">Select customer...</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.first_name} {c.last_name}
                </option>
              ))}
            </Select>
            <Input
              placeholder="Ticket ID (optional)"
              value={form.ticket_id}
              onChange={(e) => setForm({ ...form, ticket_id: e.target.value })}
            />
            <Input
              placeholder="Notes"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
            <Input
              type="date"
              placeholder="Expires"
              value={form.expires_at}
              onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
            />
            <Select
              value={form.currency}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
            >
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
              <option value="GBP">GBP (£)</option>
              <option value="CAD">CAD (C$)</option>
              <option value="AUD">AUD (A$)</option>
              <option value="JPY">JPY (¥)</option>
            </Select>
            <div className="flex gap-2">
              <Button onClick={handleCreate}>Create</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-3">
          {isLoading ? (
            <div className="p-8 text-center text-slate-400">Loading...</div>
          ) : estimates.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <FileCheck className="h-12 w-12 text-muted-foreground/40 mb-4" />
              <h3 className="text-lg font-semibold mb-1">No estimates yet</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                Create your first estimate to start quoting customers.
              </p>
              <Button
                onClick={() => setShowForm(true)}
                className="mt-4"
                variant="outline"
              >
                <Plus className="h-4 w-4 mr-1.5" />
                New Estimate
              </Button>
            </div>
          ) : (
            estimates.map((est) => {
              const cust = customers.find((c) => c.id === est.customer_id);
              return (
                <Card
                  key={est.id}
                  className={`cursor-pointer ${selectedEst?.id === est.id ? "border-primary" : "hover:border-primary/30"}`}
                  onClick={() => selectEst(est)}
                >
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        #{est.estimate_number}
                      </span>
                      <Badge variant={statusColors[est.status] || "outline"}>
                        {est.status}
                      </Badge>
                    </div>
                    <p className="font-medium mt-1">
                      {est.currency || "USD"} {est.total.toFixed(2)}
                    </p>
                    {cust && (
                      <p className="text-xs text-muted-foreground">
                        {cust.first_name} {cust.last_name}
                      </p>
                    )}
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>

        {selectedEst && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>
                  #{selectedEst.estimate_number} — $
                  {selectedEst.total.toFixed(2)}
                </CardTitle>
                {selectedEst.status === "approved" && (
                  <Button
                    size="sm"
                    variant="default"
                    onClick={() => convertMutation.mutate(selectedEst.id)}
                  >
                    <FileText className="h-3.5 w-3.5 mr-1" /> Convert to Invoice
                  </Button>
                )}
              </CardHeader>
              <CardContent className="space-y-3">
                <Select
                  value={selectedEst.status}
                  onChange={(e) => {
                    statusMutation.mutate({
                      id: selectedEst.id,
                      status: e.target.value,
                    });
                  }}
                >
                  <option value="draft">Draft</option>
                  <option value="sent">Sent</option>
                  <option value="approved">Approved</option>
                  <option value="declined">Declined</option>
                </Select>
                <div className="space-y-2">
                  {lineItems.map((li) => (
                    <div
                      key={li.id}
                      className="flex justify-between text-sm p-2 rounded bg-muted/50"
                    >
                      <div>
                        <p className="truncate">{li.description}</p>
                        <p className="text-xs text-muted-foreground">
                          {li.quantity} x ${li.unit_price.toFixed(2)}
                        </p>
                      </div>
                      <span className="font-medium shrink-0">
                        ${li.total.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Select
                    value={newItem.item_type}
                    onChange={(e) =>
                      setNewItem({ ...newItem, item_type: e.target.value })
                    }
                    className="w-24"
                  >
                    <option value="service">Service</option>
                    <option value="part">Part</option>
                  </Select>
                  <Input
                    placeholder="Description"
                    value={newItem.description}
                    onChange={(e) =>
                      setNewItem({ ...newItem, description: e.target.value })
                    }
                  />
                  <Input
                    type="number"
                    placeholder="Qty"
                    value={newItem.quantity}
                    onChange={(e) =>
                      setNewItem({ ...newItem, quantity: +e.target.value })
                    }
                    className="w-20"
                  />
                  <Input
                    type="number"
                    placeholder="Price"
                    value={newItem.unit_price}
                    onChange={(e) =>
                      setNewItem({ ...newItem, unit_price: +e.target.value })
                    }
                    className="w-24"
                  />
                  <Button size="sm" onClick={addLineItem}>
                    <Plus className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
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
