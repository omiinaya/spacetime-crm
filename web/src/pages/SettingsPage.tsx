import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api, User, MailSettings, TaxRate, WebhookSubscription, WEBHOOK_EVENTS, SmsSettings, BusinessHours } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Settings, Plus, User as UserIcon, Mail, CheckCircle, XCircle, Loader2, Percent, Webhook, Globe, Trash2, Play, Phone, Shield, ShieldAlert, Smartphone, Clock } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../lib/auth";

export default function SettingsPage() {
  return (
    <>
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage users and configuration</p>
      </div>
      <UserSettings />
      <PinSection />
      <TwoFactorSection />
      <MailSettingsSection />
      <SmsSettingsSection />
      <BusinessHoursSection />
      <TaxRateSettings />
      <SlaConfigSection />
      <WebhookSettings />
    </>
  );
}

function UserSettings() {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "staff" });

  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const res = await api.users.list();
      return res.users ?? [];
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; email: string; role: string }) =>
      api.users.create(data),
    onSuccess: () => {
      toast.success("User created");
      setShowForm(false);
      setForm({ name: "", email: "", role: "staff" });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: () => {
      toast.error("Failed to create user");
    },
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Users</CardTitle>
        <Button size="sm" onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-1" />Add User</Button>
      </CardHeader>
      <CardContent>
        {showForm && (
          <div className="flex gap-2 mb-4 p-3 rounded bg-muted/50">
            <Input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="w-32">
              <option value="admin">Admin</option>
              <option value="tech">Tech</option>
              <option value="staff">Staff</option>
            </Select>
            <Button size="sm" onClick={() => createMutation.mutate(form)}>Save</Button>
            <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        )}
        <div className="space-y-2">
          {users.map((u) => (
            <div key={u.id} className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <UserIcon className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium">{u.name}</p>
                  <p className="text-xs text-muted-foreground">{u.email}</p>
                </div>
              </div>
              <Badge variant={u.active ? "success" : "secondary"}>{u.role}</Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function MailSettingsSection() {
  const [mailConfig, setMailConfig] = useState<MailSettings>({
    host: "", port: 587, username: "", use_tls: true,
    sender_name: "SpacetimeCRM", sender_email: "", password: "",
  });
  const [testResult, setTestResult] = useState<{ ok: boolean; message?: string; error?: string } | null>(null);

  const { data: mailSettingsData } = useQuery({
    queryKey: ["mail-settings"],
    queryFn: () => api.settings.mail.get(),
  });

  const configured = mailSettingsData?.configured ?? false;

  useEffect(() => {
    if (mailSettingsData?.settings) {
      setMailConfig((prev) => ({ ...prev, ...mailSettingsData.settings!, password: "" }));
    }
  }, [mailSettingsData]);

  const saveMutation = useMutation({
    mutationFn: (data: Partial<MailSettings>) => {
      const payload = { ...data };
      if (!payload.password) delete payload.password;
      return api.settings.mail.save(payload);
    },
    onSuccess: () => {
      toast.success("Mail settings saved");
      queryClient.invalidateQueries({ queryKey: ["mail-settings"] });
    },
    onError: () => {
      toast.error("Failed to save mail settings");
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      const saveData = { ...mailConfig };
      if (!saveData.password) delete saveData.password;
      await api.settings.mail.save(saveData);
      return api.settings.mail.test();
    },
    onSuccess: (res) => {
      setTestResult(res);
      if (res.ok) {
        toast.success("SMTP connection successful");
      } else {
        toast.error("SMTP test failed");
      }
      queryClient.invalidateQueries({ queryKey: ["mail-settings"] });
    },
    onError: () => {
      toast.error("Test failed");
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-4 w-4" />
          Email Notifications
          {configured && <Badge variant="success" className="ml-2 text-xs">Configured</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Configure SMTP to send email notifications to customers when tickets are updated,
          invoices are created, appointments are scheduled, or payments are received.
        </p>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">SMTP Host</label>
            <Input placeholder="smtp.example.com" value={mailConfig.host}
              onChange={(e) => setMailConfig({ ...mailConfig, host: e.target.value })} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Port</label>
            <Input type="number" placeholder="587" value={mailConfig.port}
              onChange={(e) => setMailConfig({ ...mailConfig, port: Number(e.target.value) })} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Username</label>
            <Input placeholder="user@example.com" value={mailConfig.username}
              onChange={(e) => setMailConfig({ ...mailConfig, username: e.target.value })} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Password</label>
            <Input type="password" placeholder="••••••••" value={mailConfig.password || ""}
              onChange={(e) => setMailConfig({ ...mailConfig, password: e.target.value })} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Sender Name</label>
            <Input placeholder="SpacetimeCRM" value={mailConfig.sender_name}
              onChange={(e) => setMailConfig({ ...mailConfig, sender_name: e.target.value })} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Sender Email</label>
            <Input placeholder="noreply@example.com" value={mailConfig.sender_email}
              onChange={(e) => setMailConfig({ ...mailConfig, sender_email: e.target.value })} />
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={mailConfig.use_tls}
            onChange={(e) => setMailConfig({ ...mailConfig, use_tls: e.target.checked })}
            className="rounded border-border" />
          Use STARTTLS (recommended)
        </label>

        <div className="flex gap-2">
          <Button onClick={() => saveMutation.mutate(mailConfig)}>Save Settings</Button>
          <Button variant="outline" onClick={() => testMutation.mutate()} disabled={testMutation.isPending}>
            {testMutation.isPending ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Testing...</> : "Test Connection"}
          </Button>
        </div>

        {testResult && (
          <div className={`flex items-center gap-2 text-sm p-3 rounded ${testResult.ok ? "bg-green-500/10 text-green-600" : "bg-red-500/10 text-red-500"}`}>
            {testResult.ok ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            <span>{testResult.ok ? testResult.message || "Connected!" : testResult.error || "Connection failed"}</span>
          </div>
        )}

        <div className="border-t pt-3">
          <p className="text-xs text-muted-foreground">
            <strong>Notification triggers:</strong> Ticket status changes, new invoices,
            appointment scheduling, payment receipts, and estimate approvals
            will automatically email the customer when mail is configured.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function SmsSettingsSection() {
  const [smsConfig, setSmsConfig] = useState({ account_sid: "", from_number: "", auth_token: "" });
  const [testResult, setTestResult] = useState<{ ok: boolean; message?: string; error?: string } | null>(null);

  const { data: smsSettingsData } = useQuery({
    queryKey: ["sms-settings"],
    queryFn: () => api.settings.sms.get(),
  });

  const configured = smsSettingsData?.configured ?? false;

  useEffect(() => {
    if (smsSettingsData?.settings) {
      setSmsConfig((prev) => ({
        ...prev,
        account_sid: smsSettingsData.settings!.account_sid || "",
        from_number: smsSettingsData.settings!.from_number || "",
      }));
    }
  }, [smsSettingsData]);

  const saveMutation = useMutation({
    mutationFn: (data: { account_sid?: string; auth_token?: string; from_number?: string }) => {
      const payload = { ...data };
      if (!payload.auth_token) (payload as any).auth_token = undefined;
      return api.settings.sms.save(payload);
    },
    onSuccess: () => {
      toast.success("SMS settings saved");
      queryClient.invalidateQueries({ queryKey: ["sms-settings"] });
    },
    onError: () => {
      toast.error("Failed to save SMS settings");
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      const saveData = { ...smsConfig };
      if (!saveData.auth_token) (saveData as any).auth_token = undefined;
      await api.settings.sms.save(saveData);
      return api.settings.sms.test();
    },
    onSuccess: (res) => {
      setTestResult(res);
      if (res.ok) {
        toast.success("Twilio connection successful");
      } else {
        toast.error("Twilio test failed");
      }
      queryClient.invalidateQueries({ queryKey: ["sms-settings"] });
    },
    onError: () => {
      toast.error("Test failed");
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Phone className="h-4 w-4" />
          SMS Notifications (Twilio)
          {configured && <Badge variant="success" className="ml-2 text-xs">Configured</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Configure Twilio to send SMS notifications to customers when tickets are updated,
          invoices are created, payments are received, appointments are scheduled, or estimates are approved.
          Messages are sent to the customer's <strong>mobile</strong> phone number.
        </p>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Twilio Account SID</label>
            <Input placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" value={smsConfig.account_sid}
              onChange={(e) => setSmsConfig({ ...smsConfig, account_sid: e.target.value })} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Auth Token</label>
            <Input type="password" placeholder="xxxxxxxxxxxxxxxxxxxxxxxx" value={smsConfig.auth_token}
              onChange={(e) => setSmsConfig({ ...smsConfig, auth_token: e.target.value })} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">From Number</label>
            <Input placeholder="+15551234567" value={smsConfig.from_number}
              onChange={(e) => setSmsConfig({ ...smsConfig, from_number: e.target.value })} />
          </div>
        </div>

        <div className="flex gap-2">
          <Button onClick={() => saveMutation.mutate(smsConfig)}>Save Settings</Button>
          <Button variant="outline" onClick={() => testMutation.mutate()} disabled={testMutation.isPending}>
            {testMutation.isPending ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Testing...</> : "Test Connection"}
          </Button>
        </div>

        {testResult && (
          <div className={`flex items-center gap-2 text-sm p-3 rounded ${testResult.ok ? "bg-green-500/10 text-green-600" : "bg-red-500/10 text-red-500"}`}>
            {testResult.ok ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            <span>{testResult.ok ? testResult.message || "Connected!" : testResult.error || "Connection failed"}</span>
          </div>
        )}

        <div className="border-t pt-3">
          <p className="text-xs text-muted-foreground">
            <strong>Notification triggers:</strong> Ticket status changes, new invoices,
            payment receipts, appointment scheduling, and estimate approvals
            will automatically send an SMS to the customer's mobile number when Twilio is configured.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function TaxRateSettings() {
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
    mutationFn: ({ id, data }: { id: string; data: { name: string; rate: number; is_default: boolean } }) =>
      api.taxRates.update(id, data),
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
        <Button size="sm" onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-1" />Add Tax Rate</Button>
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
              onChange={(e) => setForm({ ...form, rate: parseFloat(e.target.value) || 0 })}
            />
            <label className="flex items-center gap-1.5 text-sm whitespace-nowrap">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
                className="rounded border-border"
              />
              Default
            </label>
            <Button size="sm" onClick={() => createMutation.mutate(form)}>Save</Button>
            <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        )}
        {taxRates.length === 0 ? (
          <p className="text-sm text-muted-foreground">No tax rates configured.</p>
        ) : (
          <div className="space-y-2">
            {taxRates.map((tr) => (
              <div key={tr.id} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Percent className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">
                      {tr.name}
                      {tr.is_default && <Badge variant="success" className="ml-2 text-xs">Default</Badge>}
                    </p>
                    <p className="text-xs text-muted-foreground">{tr.rate}%</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => updateMutation.mutate({ id: tr.id, data: { name: tr.name, rate: tr.rate, is_default: !tr.is_default } })}>
                    {tr.is_default ? "Unset Default" : "Set Default"}
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => deleteMutation.mutate(tr.id)}>Delete</Button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="border-t pt-3 mt-3">
          <p className="text-xs text-muted-foreground">
            Tax rates are applied to invoices and estimates. The default rate is pre-selected when creating new invoices.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function WebhookSettings() {
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

function PinSection() {
  const { user } = useAuth();
  const [pin, setPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [busy, setBusy] = useState(false);

  if (!user) return null;

  const handleSetPin = async () => {
    if (!pin || pin.length < 4 || pin.length > 10) {
      toast.error("PIN must be 4–10 digits");
      return;
    }
    if (pin !== confirmPin) {
      toast.error("PINs do not match");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/auth/set-pin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin }),
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || "Failed to set PIN");
        return;
      }
      toast.success("POS PIN set successfully");
      setPin("");
      setConfirmPin("");
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Smartphone className="h-4 w-4" />
          POS PIN Login
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Set a numeric PIN for quick POS terminal login. PIN is stored as a bcrypt hash
          and used at the POS counter for fast check-in without entering your full password.
        </p>
        <div className="flex gap-2 items-end">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">New PIN (4–10 digits)</label>
            <Input
              type="password"
              placeholder="Enter PIN"
              maxLength={10}
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Confirm PIN</label>
            <Input
              type="password"
              placeholder="Confirm PIN"
              maxLength={10}
              value={confirmPin}
              onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, ""))}
            />
          </div>
          <Button onClick={handleSetPin} disabled={busy}>
            {busy ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Saving...</> : "Set PIN"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function TwoFactorSection() {
  const { user, token } = useAuth();
  const [step, setStep] = useState<"idle" | "setup" | "verify">("idle");
  const [secret, setSecret] = useState("");
  const [provisioningUri, setProvisioningUri] = useState("");
  const [verifyCode, setVerifyCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [isEnrolled, setIsEnrolled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showDisable, setShowDisable] = useState(false);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch("/api/auth/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        setIsEnrolled(data.totp_enabled ?? false);
      } catch {}
    };
    if (token) check();
  }, [token]);

  if (!user) return null;

  const handleSetup = async () => {
    setBusy(true);
    try {
      const res = await fetch("/api/auth/setup-2fa", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || "Setup failed");
        return;
      }
      const data = await res.json();
      setSecret(data.secret);
      setProvisioningUri(data.provisioning_uri);
      setStep("verify");
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async () => {
    if (verifyCode.length !== 6) return;
    setBusy(true);
    try {
      const res = await fetch("/api/auth/verify-2fa", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ code: verifyCode }),
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || "Verification failed");
        return;
      }
      toast.success("2FA enabled successfully");
      setIsEnrolled(true);
      setStep("idle");
      setSecret("");
      setVerifyCode("");
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleDisable = async () => {
    if (disableCode.length !== 6) return;
    setBusy(true);
    try {
      const res = await fetch("/api/auth/disable-2fa", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ code: disableCode }),
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || "Disable failed");
        return;
      }
      toast.success("2FA disabled");
      setIsEnrolled(false);
      setShowDisable(false);
      setDisableCode("");
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="w-4 h-4" /> Two-Factor Authentication
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isEnrolled ? (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <ShieldAlert className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium text-green-500">2FA is enabled</span>
            </div>
            {!showDisable ? (
              <Button variant="outline" size="sm" onClick={() => setShowDisable(true)}>
                Disable 2FA
              </Button>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  Enter a current 2FA code from your authenticator app to disable.
                </p>
                <div className="flex gap-2">
                  <Input
                    placeholder="000000"
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    className="w-32 font-mono text-center"
                    maxLength={6}
                  />
                  <Button size="sm" onClick={handleDisable} disabled={busy || disableCode.length !== 6}>
                    {busy ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                    Disable
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => { setShowDisable(false); setDisableCode(""); }}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        ) : step === "idle" ? (
          <div>
            <p className="text-sm text-muted-foreground mb-3">
              Add an extra layer of security to your account by enabling two-factor authentication.
            </p>
            <Button size="sm" onClick={handleSetup} disabled={busy}>
              {busy ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Smartphone className="w-3 h-3 mr-1" />}
              Set up 2FA
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm font-medium">Step 1: Scan this QR code</p>
            <p className="text-xs text-muted-foreground">
              Use your authenticator app (Google Authenticator, Authy, etc.) to scan the QR code below.
            </p>
            <div className="flex justify-center">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(provisioningUri)}`}
                alt="2FA QR Code"
                className="border rounded-lg"
                style={{ imageRendering: "pixelated" }}
              />
            </div>
            <div className="text-center">
              <p className="text-xs text-muted-foreground">Or enter this key manually:</p>
              <code className="text-xs bg-muted px-2 py-1 rounded select-all">{secret}</code>
            </div>
            <div className="border-t pt-3">
              <p className="text-sm font-medium mb-2">Step 2: Verify the code</p>
              <div className="flex gap-2">
                <Input
                  placeholder="000000"
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  className="w-32 font-mono text-center"
                  maxLength={6}
                  autoFocus
                />
                <Button size="sm" onClick={handleVerify} disabled={busy || verifyCode.length !== 6}>
                  {busy ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                  Verify & Enable
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setStep("idle")}>
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SlaConfigSection() {
  const [targets, setTargets] = useState<Record<string, number>>({
    urgent: 4,
    high: 24,
    medium: 72,
    low: 120,
  });
  const [editing, setEditing] = useState(false);
  const [dirty, setDirty] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["sla-settings"],
    queryFn: async () => {
      const res = await api.tickets.sla.settings();
      setTargets(res.targets);
      return res;
    },
  });

  const saveMutation = useMutation({
    mutationFn: (t: Record<string, number>) => api.tickets.sla.save(t),
    onSuccess: () => {
      toast.success("SLA targets saved");
      setEditing(false);
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["sla-settings"] });
      queryClient.invalidateQueries({ queryKey: ["tickets", "sla-breaches"] });
    },
    onError: () => {
      toast.error("Failed to save SLA targets");
    },
  });

  const handleChange = (key: string, raw: string) => {
    const val = parseFloat(raw);
    if (!isNaN(val) && val > 0) {
      setTargets((prev) => ({ ...prev, [key]: val }));
      setDirty(true);
    }
  };

  const labelMap: Record<string, string> = {
    urgent: "Urgent",
    high: "High",
    medium: "Medium",
    low: "Low",
  };

  const helpMap: Record<string, string> = {
    urgent: "Response expected within 4 hours",
    high: "Response expected within 24 hours",
    medium: "Response expected within 3 days",
    low: "Response expected within 5 days",
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4" />
          SLA Targets
        </CardTitle>
        {!editing ? (
          <Button size="sm" onClick={() => setEditing(true)} disabled={isLoading}>
            Edit
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setTargets(data?.targets ?? { urgent: 4, high: 24, medium: 72, low: 120 });
                setEditing(false);
                setDirty(false);
              }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={() => saveMutation.mutate(targets)}
              disabled={!dirty || saveMutation.isPending}
            >
              {saveMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
              Save
            </Button>
          </div>
        )}
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          Thresholds in hours after which a ticket is considered breaching SLA.
          Changes take effect immediately on the next SLA breach scan (auto-refresh every 60s).
        </p>
        <div className="space-y-4">
          {["urgent", "high", "medium", "low"].map((key) => (
            <div key={key} className="flex items-center gap-4">
              <label className="w-24 text-sm font-medium text-right">{labelMap[key]}</label>
              {editing ? (
                <Input
                  type="number"
                  min={1}
                  max={8760}
                  value={targets[key] ?? ""}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="w-28"
                />
              ) : (
                <span className="text-sm font-mono tabular-nums w-28">
                  {targets[key] ?? "-"}h
                </span>
              )}
              <span className="text-xs text-muted-foreground">{helpMap[key]}</span>
            </div>
          ))}
        </div>
        {!editing && data?.updated_at ? (
          <p className="text-xs text-muted-foreground mt-4">
            Last updated: {new Date(data.updated_at).toLocaleString()}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

// ── Business Hours Section ──────────────────────────────────────

const DAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] as const;
const DAY_LABELS: Record<string, string> = {
  monday: "Monday", tuesday: "Tuesday", wednesday: "Wednesday",
  thursday: "Thursday", friday: "Friday", saturday: "Saturday", sunday: "Sunday",
};

const defaultHours: BusinessHours = {
  monday: { enabled: true, open: "09:00", close: "18:00" },
  tuesday: { enabled: true, open: "09:00", close: "18:00" },
  wednesday: { enabled: true, open: "09:00", close: "18:00" },
  thursday: { enabled: true, open: "09:00", close: "18:00" },
  friday: { enabled: true, open: "09:00", close: "18:00" },
  saturday: { enabled: false, open: "10:00", close: "14:00" },
  sunday: { enabled: false, open: "10:00", close: "14:00" },
};

function BusinessHoursSection() {
  const [hours, setHours] = useState<BusinessHours>(defaultHours);

  const { data: hoursData } = useQuery({
    queryKey: ["business-hours"],
    queryFn: () => api.settings.businessHours.get(),
  });

  useEffect(() => {
    if (hoursData?.hours) {
      setHours({ ...defaultHours, ...hoursData.hours });
    }
  }, [hoursData]);

  const saveMutation = useMutation({
    mutationFn: (data: BusinessHours) => api.settings.businessHours.save(data),
    onSuccess: () => {
      toast.success("Business hours saved");
      queryClient.invalidateQueries({ queryKey: ["business-hours"] });
    },
    onError: () => toast.error("Failed to save business hours"),
  });

  const updateDay = (day: string, field: string, value: boolean | string) => {
    setHours((prev) => ({
      ...prev,
      [day]: { ...prev[day as keyof BusinessHours], [field]: value },
    }));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Business Hours
          {hoursData?.configured && <Badge variant="success" className="ml-2 text-xs">Configured</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Set your shop's operating hours. These determine when appointments can be scheduled
          and which time slots are available in the calendar.
        </p>

        <div className="space-y-2">
          {DAY_KEYS.map((day) => (
            <div key={day} className="flex items-center gap-3 p-2 rounded bg-muted/30">
              <label className="flex items-center gap-2 w-28">
                <input
                  type="checkbox"
                  checked={hours[day].enabled}
                  onChange={(e) => updateDay(day, "enabled", e.target.checked)}
                  className="rounded border-border accent-primary"
                />
                <span className={`text-sm font-medium ${hours[day].enabled ? "" : "text-muted-foreground line-through"}`}>
                  {DAY_LABELS[day]}
                </span>
              </label>
              {hours[day].enabled ? (
                <>
                  <Input
                    type="time"
                    value={hours[day].open}
                    onChange={(e) => updateDay(day, "open", e.target.value)}
                    className="w-28"
                  />
                  <span className="text-xs text-muted-foreground">to</span>
                  <Input
                    type="time"
                    value={hours[day].close}
                    onChange={(e) => updateDay(day, "close", e.target.value)}
                    className="w-28"
                  />
                </>
              ) : (
                <span className="text-xs text-muted-foreground italic">Closed</span>
              )}
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <Button onClick={() => saveMutation.mutate(hours)} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Saving...</> : "Save Hours"}
          </Button>
          <Button variant="outline" onClick={() => setHours(defaultHours)}>Reset to Defaults</Button>
        </div>

        <div className="border-t pt-3">
          <p className="text-xs text-muted-foreground">
            <strong>How this is used:</strong> The appointment scheduler will only offer 
            time slots within operating hours. Days marked as closed won't appear 
            in the date picker. Future features will add lunch breaks and holiday closures.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}