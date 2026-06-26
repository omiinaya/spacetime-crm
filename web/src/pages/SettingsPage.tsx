import { useState, useEffect } from "react";
import { api, User } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Settings, Plus, User as UserIcon } from "lucide-react";
import { toast } from "sonner";

export default function SettingsPage() {
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
    <>
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage users and configuration</p>
      </div>

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
    </>
  );
}
