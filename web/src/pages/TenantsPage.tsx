import { useState, useEffect } from "react";
import { toast } from "sonner";
import {
  Building2,
  Plus,
  Trash2,
  Edit3,
  Users,
  UserPlus,
  X,
  RefreshCw,
  Shield,
  User,
} from "lucide-react";
import { api } from "../lib/api";
import { useAuth, hasRole } from "../lib/auth";
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Badge } from "../components/ui/badge";

interface Tenant {
  id: string;
  name: string;
  slug: string;
  logo_url: string;
  settings: string;
  created_at: number;
  updated_at: number;
}

interface TenantMember {
  id: string;
  tenant_id: string;
  username: string;
  role: string;
  created_at: number;
}

export default function TenantsPage() {
  const { user, refreshTenant } = useAuth();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selected, setSelected] = useState<Tenant | null>(null);
  const [members, setMembers] = useState<TenantMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showAddMember, setShowAddMember] = useState(false);
  const [editTenant, setEditTenant] = useState<Tenant | null>(null);
  const [migrating, setMigrating] = useState(false);

  // Create form
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");

  // Edit form
  const [editName, setEditName] = useState("");
  const [editSlug, setEditSlug] = useState("");

  // Member form
  const [memberUsername, setMemberUsername] = useState("");
  const [memberRole, setMemberRole] = useState("user");

  const load = async () => {
    try {
      const data = await api.tenants.list();
      setTenants(data.tenants || []);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const loadMembers = async (tenantId: string) => {
    try {
      const data = await api.tenants.get(tenantId);
      setMembers(data.tenant?.members || []);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const selectTenant = async (t: Tenant) => {
    setSelected(t);
    await loadMembers(t.id);
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      await api.tenants.create({
        name: newName.trim(),
        slug: newSlug.trim() || undefined,
      });
      toast.success("Tenant created");
      setShowCreate(false);
      setNewName("");
      setNewSlug("");
      await load();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleEdit = async () => {
    if (!editTenant || !editName.trim()) return;
    try {
      await api.tenants.update(editTenant.id, {
        name: editName.trim(),
        slug: editSlug.trim() || undefined,
      });
      toast.success("Tenant updated");
      setEditTenant(null);
      await load();
      if (selected?.id === editTenant.id) {
        setSelected({
          ...selected,
          name: editName.trim(),
          slug: editSlug.trim(),
        });
      }
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this tenant and all its data?")) return;
    try {
      await api.tenants.delete(id);
      toast.success("Tenant deleted");
      if (selected?.id === id) {
        setSelected(null);
        setMembers([]);
      }
      await load();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleAddMember = async () => {
    if (!selected || !memberUsername.trim()) return;
    try {
      await api.tenants.addMember(selected.id, {
        username: memberUsername.trim(),
        role: memberRole,
      });
      toast.success("Member added");
      setShowAddMember(false);
      setMemberUsername("");
      setMemberRole("user");
      await loadMembers(selected.id);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!selected) return;
    try {
      await api.tenants.removeMember(selected.id, memberId);
      toast.success("Member removed");
      await loadMembers(selected.id);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleMigrate = async () => {
    setMigrating(true);
    try {
      const result = await api.tenants.migrate({ name: "Default" });
      toast.success(`Migrated: ${result.users_migrated} users assigned`);
      await load();
      await refreshTenant();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setMigrating(false);
    }
  };

  const isAdmin = hasRole(user, "admin");

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tenants</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage organizations and team access
          </p>
        </div>
        <div className="flex gap-2">
          {tenants.length === 0 && isAdmin && (
            <Button
              variant="outline"
              onClick={handleMigrate}
              disabled={migrating}
            >
              <RefreshCw
                className={`h-4 w-4 mr-2 ${migrating ? "animate-spin" : ""}`}
              />
              Migrate from Single-Tenant
            </Button>
          )}
          {isAdmin && (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Tenant
            </Button>
          )}
        </div>
      </div>

      {/* Create dialog */}
      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Create Tenant
              <button onClick={() => setShowCreate(false)}>
                <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
              </button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground">Name *</label>
              <input
                className="w-full px-3 py-2 rounded-md border border-border bg-background text-sm"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My Repair Shop"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">
                Slug (URL-friendly)
              </label>
              <input
                className="w-full px-3 py-2 rounded-md border border-border bg-background text-sm"
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value)}
                placeholder="my-repair-shop"
              />
            </div>
            <Button onClick={handleCreate} disabled={!newName.trim()}>
              Create
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tenant list */}
        <Card>
          <CardHeader>
            <CardTitle>All Tenants</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {tenants.length === 0 && (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No tenants yet. Create one or run the migration.
              </p>
            )}
            {tenants.map((t) => (
              <div
                key={t.id}
                className={`flex items-center justify-between p-3 rounded-md border cursor-pointer transition-colors ${
                  selected?.id === t.id
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-muted"
                }`}
                onClick={() => selectTenant(t)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-1.5 rounded-md bg-muted shrink-0">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{t.name}</p>
                    <p className="text-xs text-muted-foreground">{t.slug}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {isAdmin && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditTenant(t);
                          setEditName(t.name);
                          setEditSlug(t.slug);
                        }}
                        className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(t.id);
                        }}
                        className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Tenant detail / members */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Members</span>
              {selected && isAdmin && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowAddMember(true)}
                >
                  <UserPlus className="h-3.5 w-3.5 mr-1" />
                  Add
                </Button>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!selected && (
              <p className="text-sm text-muted-foreground py-8 text-center">
                Select a tenant to view members
              </p>
            )}
            {selected && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-3 p-2 rounded-md bg-muted/50">
                  <Building2 className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">{selected.name}</span>
                </div>
                {members.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No members yet
                  </p>
                )}
                {members.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center justify-between p-2 rounded-md hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{m.username}</span>
                      <Badge
                        variant={m.role === "admin" ? "default" : "secondary"}
                        className="text-[10px] px-1.5 py-0"
                      >
                        {m.role}
                      </Badge>
                    </div>
                    {isAdmin && (
                      <button
                        onClick={() => handleRemoveMember(m.id)}
                        className="p-1 rounded-md hover:bg-muted text-muted-foreground hover:text-destructive"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                ))}

                {/* Current user indicator */}
                {user?.tenant_id === selected?.id && (
                  <div className="mt-3 p-2 rounded-md bg-primary/5 border border-primary/20">
                    <p className="text-xs text-primary flex items-center gap-1">
                      <Shield className="h-3 w-3" />
                      Your current tenant
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Add member dialog */}
            {showAddMember && selected && (
              <div className="mt-4 p-3 border border-border rounded-md space-y-2">
                <p className="text-xs font-medium">Add Member</p>
                <input
                  className="w-full px-2 py-1.5 rounded-md border border-border bg-background text-sm"
                  value={memberUsername}
                  onChange={(e) => setMemberUsername(e.target.value)}
                  placeholder="Username (e.g. user.name)"
                />
                <select
                  className="w-full px-2 py-1.5 rounded-md border border-border bg-background text-sm"
                  value={memberRole}
                  onChange={(e) => setMemberRole(e.target.value)}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={handleAddMember}
                    disabled={!memberUsername.trim()}
                  >
                    <UserPlus className="h-3.5 w-3.5 mr-1" />
                    Add
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowAddMember(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Edit dialog */}
      {editTenant && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Edit Tenant
                <button onClick={() => setEditTenant(null)}>
                  <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                </button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className="text-xs text-muted-foreground">Name</label>
                <input
                  className="w-full px-3 py-2 rounded-md border border-border bg-background text-sm"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Slug</label>
                <input
                  className="w-full px-3 py-2 rounded-md border border-border bg-background text-sm"
                  value={editSlug}
                  onChange={(e) => setEditSlug(e.target.value)}
                />
              </div>
              <Button onClick={handleEdit} disabled={!editName.trim()}>
                Save
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
