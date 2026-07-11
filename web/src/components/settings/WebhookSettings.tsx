import { Globe, Loader2, Play, Plus, Settings, Trash2, Webhook } from "lucide-react";
import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../../lib/query-client";
import { api, WebhookSubscription, WEBHOOK_EVENTS } from "../../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Select } from "../ui/select";
import { Badge } from "../ui/badge";
import { toast } from "sonner";

export default function WebhookSettings() {
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ url: "", events: "", secret: "" });
  const [testing, setTesting] = useState<string | null>(null);

  const { data: subscriptions = [] } = useQuery({
    queryKey: ["webhooks"],
    queryFn: async () => {
      const res = await api.webhooks.list();
      return res.subscriptions ?? [];
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: { url: string; events: string; secret?: string }) =>
      editingId ? api.webhooks.update(editingId, data) : api.webhooks.create(data),
    onSuccess: () => {
      toast.success(editingId ? "Webhook updated" : "Webhook created");
      setShowForm(false);
      setEditingId(null);
      setForm({ url: "", events: "", secret: "" });
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
    },
    onError: () => {
      toast.error("Failed to save webhook");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.webhooks.delete(id),
    onSuccess: () => {
      toast.success("Webhook deleted");
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
    },
    onError: () => {
      toast.error("Failed to delete");
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (sub: WebhookSubscription) =>
      api.webhooks.update(sub.id, {
        url: sub.url,
        events: sub.events,
        active: !sub.active,
      }),
    onSuccess: (_data, sub) => {
      toast.success(sub.active ? "Webhook paused" : "Webhook resumed");
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
    },
    onError: () => {
      toast.error("Failed to toggle");
    },
  });

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const res = await api.webhooks.test(id);
      if (res.ok) {
        toast.success("Test sent - HTTP " + res.status_code);
      } else {
        toast.error("Test failed: " + (res.error || "Unknown"));
      }
    } catch { toast.error("Test request failed"); }
    finally { setTesting(null); }
  };

  const handleCreate = () => {
    if (!form.url || !form.events) {
      toast.error("URL and events are required");
      return;
    }
    createMutation.mutate(form);
  };

  const handleEdit = (sub: WebhookSubscription) => {
    setForm({ url: sub.url, events: sub.events, secret: sub.secret || "" });
    setEditingId(sub.id);
    setShowForm(true);
  };

  const toggleEvent = (event: string) => {
    const current = form.events ? form.events.split(",").map(e => e.trim()).filter(Boolean) : [];
    const idx = current.indexOf(event);
    if (idx >= 0) {
      current.splice(idx, 1);
    } else {
      current.push(event);
    }
    setForm({ ...form, events: current.join(",") });
  };

  const eventGroups: { label: string; events: string[] }[] = [
    { label: "Customers", events: ["customer.created", "customer.updated", "customer.deleted"] },
    { label: "Tickets", events: ["ticket.created", "ticket.updated", "ticket.status_changed"] },
    { label: "Invoices", events: ["invoice.created", "invoice.status_changed", "invoice.paid"] },
    { label: "Payments", events: ["payment.created"] },
    { label: "Estimates", events: ["estimate.created", "estimate.approved"] },
    { label: "Appointments", events: ["appointment.created"] },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Globe className="h-4 w-4" />
          Webhook Integrations
        </CardTitle>
        <Button size="sm" onClick={() => { setShowForm(true); setEditingId(null); setForm({ url: "", events: "", secret: "" }); }}>
          <Plus className="h-4 w-4 mr-1" />Add Webhook
        </Button>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          Webhooks allow external services to receive real-time notifications when events
          happen in the CRM. Each webhook URL receives a POST request with a JSON payload
          signed with HMAC-SHA256.
        </p>

        {showForm && (
          <div className="mb-4 p-4 rounded bg-muted/50 space-y-3">
            <div>
              <label className="text-xs text-muted-foreground block mb-1">Endpoint URL</label>
              <Input
                placeholder="https://example.com/webhook"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground block mb-1">
                Secret (for HMAC signing - optional)
              </label>
              <Input
                type="password"
                placeholder="Optional signing secret"
                value={form.secret}
                onChange={(e) => setForm({ ...form, secret: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground block mb-2">Events to subscribe to</label>
              <div className="space-y-2">
                {eventGroups.map((group) => (
                  <div key={group.label}>
                    <p className="text-xs font-medium text-muted-foreground mb-1">{group.label}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {group.events.map((ev) => {
                        const selected = form.events.includes(ev);
                        return (
                          <button
                            key={ev}
                            type="button"
                            onClick={() => toggleEvent(ev)}
                            className={"text-xs px-2.5 py-1 rounded-full border transition-colors " + (
                              selected
                                ? "bg-primary text-primary-foreground border-primary"
                                : "bg-background text-muted-foreground border-border hover:border-primary/50"
                            )}
                          >
                            {ev}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button size="sm" onClick={handleCreate}>
                {editingId ? "Update" : "Create"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => { setShowForm(false); setEditingId(null); }}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {subscriptions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No webhook subscriptions configured.</p>
        ) : (
          <div className="space-y-2">
            {subscriptions.map((sub) => (
              <div key={sub.id} className="flex items-start justify-between py-3 border-b border-border/50 last:border-0">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={"w-2 h-2 rounded-full " + (sub.active ? "bg-green-500" : "bg-gray-400")} />
                    <p className="text-sm font-medium truncate">{sub.url}</p>
                    <Badge variant={sub.active ? "success" : "secondary"}>
                      {sub.active ? "Active" : "Paused"}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 truncate">
                    Events: {sub.events}
                  </p>
                </div>
                <div className="flex gap-1 ml-3 shrink-0">
                  <Button size="sm" variant="outline" onClick={() => handleTest(sub.id)} disabled={testing === sub.id}>
                    {testing === sub.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleEdit(sub)}>
                    Edit
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => toggleMutation.mutate(sub)}>
                    {sub.active ? "Pause" : "Resume"}
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => deleteMutation.mutate(sub.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="border-t pt-3 mt-3">
          <p className="text-xs text-muted-foreground">
            <strong>Payload format:</strong> Each webhook POST includes a JSON body with
            <code> event</code>, <code> timestamp</code>, and <code> data</code> fields.
            The <code>X-Webhook-Signature</code> header contains the HMAC-SHA256 hex digest
            of the body using the configured secret.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

