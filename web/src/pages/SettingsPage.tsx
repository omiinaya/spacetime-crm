import { useState, useEffect } from "react";
import { api, User, MailSettings, TaxRate, WebhookSubscription, WEBHOOK_EVENTS, SmsSettings } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Settings, Plus, User as UserIcon, Mail, CheckCircle, XCircle, Loader2, Percent, Webhook, Globe, Trash2, Play, Phone } from "lucide-react";
import { toast } from "sonner";

export default function SettingsPage() {
  return (
    <>
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage users and configuration</p>
      </div>
      <UserSettings />
      <MailSettingsSection />
      <SmsSettingsSection />
      <TaxRateSettings />
      <WebhookSettings />
    </>
  );
}

function UserSettings() {
  const [users, setUsers] = useState<User[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "staff" });

  const load = async () => {
    try {
      const res = await api.users.list();
      setUsers(res.users);
    } catch { /* silently fail */ }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    try {
      await api.users.create(form);
      toast.success("User created");
      setShowForm(false);
      setForm({ name: "", email: "", role: "staff" });
      load();
    } catch { toast.error("Failed to create user"); }
  };

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
            <Button size="sm" onClick={handleCreate}>Save</Button>
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
  const [configured, setConfigured] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message?: string; error?: string } | null>(null);

  useEffect(() => {
    api.settings.mail.get().then((res) => {
      setConfigured(res.configured);
      if (res.settings) {
        setMailConfig({ ...mailConfig, ...res.settings, password: "" });
      }
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    const data = { ...mailConfig };
    if (!data.password) delete data.password;
    try {
      await api.settings.mail.save(data);
      toast.success("Mail settings saved");
      setConfigured(true);
    } catch { toast.error("Failed to save mail settings"); }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      // Save first, then test
      const data = { ...mailConfig };
      if (!data.password) delete data.password;
      await api.settings.mail.save(data);
      const res = await api.settings.mail.test();
      setTestResult(res);
      if (res.ok) {
        toast.success("SMTP connection successful");
      } else {
        toast.error("SMTP test failed");
      }
    } catch { toast.error("Test failed"); }
    finally { setTesting(false); }
  };

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
          <Button onClick={handleSave}>Save Settings</Button>
          <Button variant="outline" onClick={handleTest} disabled={testing}>
            {testing ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Testing...</> : "Test Connection"}
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
  const [configured, setConfigured] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message?: string; error?: string } | null>(null);

  useEffect(() => {
    api.settings.sms.get().then((res) => {
      setConfigured(res.configured);
      if (res.settings) {
        setSmsConfig({ ...smsConfig, account_sid: res.settings.account_sid || "", from_number: res.settings.from_number || "" });
      }
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    const data = { ...smsConfig };
    if (!data.auth_token) (data as any).auth_token = undefined;
    try {
      await api.settings.sms.save(data);
      toast.success("SMS settings saved");
      setConfigured(true);
    } catch { toast.error("Failed to save SMS settings"); }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const data = { ...smsConfig };
      if (!data.auth_token) (data as any).auth_token = undefined;
      await api.settings.sms.save(data);
      const res = await api.settings.sms.test();
      setTestResult(res);
      if (res.ok) {
        toast.success("Twilio connection successful");
      } else {
        toast.error("Twilio test failed");
      }
    } catch { toast.error("Test failed"); }
    finally { setTesting(false); }
  };

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
          <Button onClick={handleSave}>Save Settings</Button>
          <Button variant="outline" onClick={handleTest} disabled={testing}>
            {testing ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Testing...</> : "Test Connection"}
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
  const [taxRates, setTaxRates] = useState<TaxRate[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", rate: 0, is_default: false });

  const load = async () => {
    try {
      const res = await api.taxRates.list();
      setTaxRates(res.tax_rates);
    } catch { /* silently fail */ }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    try {
      await api.taxRates.create(form);
      toast.success("Tax rate created");
      setShowForm(false);
      setForm({ name: "", rate: 0, is_default: false });
      load();
    } catch { toast.error("Failed to create tax rate"); }
  };

  const handleToggleDefault = async (tr: TaxRate) => {
    try {
      await api.taxRates.update(tr.id, { name: tr.name, rate: tr.rate, is_default: !tr.is_default });
      toast.success("Default updated");
      load();
    } catch { toast.error("Failed to update"); }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.taxRates.delete(id);
      toast.success("Tax rate deleted");
      load();
    } catch { toast.error("Failed to delete"); }
  };

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
            <Button size="sm" onClick={handleCreate}>Save</Button>
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
                  <Button size="sm" variant="outline" onClick={() => handleToggleDefault(tr)}>
                    {tr.is_default ? "Unset Default" : "Set Default"}
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => handleDelete(tr.id)}>Delete</Button>
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
  const [subscriptions, setSubscriptions] = useState<WebhookSubscription[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ url: "", events: "", secret: "" });
  const [testing, setTesting] = useState<string | null>(null);

  const load = async () => {
    try {
      const res = await api.webhooks.list();
      setSubscriptions(res.subscriptions);
    } catch { /* silently fail */ }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.url || !form.events) {
      toast.error("URL and events are required");
      return;
    }
    try {
      if (editingId) {
        await api.webhooks.update(editingId, form);
        toast.success("Webhook updated");
      } else {
        await api.webhooks.create(form);
        toast.success("Webhook created");
      }
      setShowForm(false);
      setEditingId(null);
      setForm({ url: "", events: "", secret: "" });
      load();
    } catch { toast.error("Failed to save webhook"); }
  };

  const handleEdit = (sub: WebhookSubscription) => {
    setForm({ url: sub.url, events: sub.events, secret: sub.secret || "" });
    setEditingId(sub.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await api.webhooks.delete(id);
      toast.success("Webhook deleted");
      load();
    } catch { toast.error("Failed to delete"); }
  };

  const handleToggle = async (sub: WebhookSubscription) => {
    try {
      await api.webhooks.update(sub.id, {
        url: sub.url,
        events: sub.events,
        active: !sub.active,
      });
      toast.success(sub.active ? "Webhook paused" : "Webhook resumed");
      load();
    } catch { toast.error("Failed to toggle"); }
  };

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
                  <Button size="sm" variant="outline" onClick={() => handleToggle(sub)}>
                    {sub.active ? "Pause" : "Resume"}
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => handleDelete(sub.id)}>
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
