import { useState, useEffect } from "react";
import { api, User, MailSettings } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Settings, Plus, User as UserIcon, Mail, CheckCircle, XCircle, Loader2 } from "lucide-react";
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
