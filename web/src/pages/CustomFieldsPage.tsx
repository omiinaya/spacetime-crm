import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Plus, Edit2, Trash2, GripVertical, Save, X,
} from "lucide-react";

interface FieldDef {
  id: string;
  entity_type: string;
  label: string;
  field_type: string;
  options: string;
  sort_order: number;
  required: boolean;
  active: boolean;
  created_at: number;
  updated_at: number;
}

const ENTITY_TYPES = ["customer", "ticket", "invoice", "product", "estimate", "purchase_order"];
const FIELD_TYPES = ["text", "number", "date", "select", "multiselect", "checkbox", "textarea"];

const entityColor = (t: string) => {
  const m: Record<string, string> = {
    customer: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    ticket: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    invoice: "bg-green-500/10 text-green-500 border-green-500/20",
    product: "bg-purple-500/10 text-purple-500 border-purple-500/20",
    estimate: "bg-cyan-500/10 text-cyan-500 border-cyan-500/20",
    purchase_order: "bg-pink-500/10 text-pink-500 border-pink-500/20",
  };
  return m[t] || "bg-gray-500/10 text-gray-500 border-gray-500/20";
};

export default function CustomFieldsPage() {
  const [editing, setEditing] = useState<FieldDef | null>(null);
  const [creating, setCreating] = useState(false);
  const [filterEntity, setFilterEntity] = useState("");

  const { data: definitions = [], isLoading } = useQuery({
    queryKey: ["custom-fields", filterEntity ?? ""],
    queryFn: async () => {
      const res = await api.customFields.definitions.list(
        filterEntity || undefined
      );
      return res.definitions ?? [];
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.customFields.definitions.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-fields"] });
    },
  });

  const handleDelete = (id: string, label: string) => {
    if (!confirm(`Delete custom field "${label}"? This cannot be undone.`)) return;
    deleteMutation.mutate(id);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Custom Fields</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Define custom data fields for customers, tickets, invoices, and more
          </p>
        </div>
        <Button onClick={() => { setCreating(true); setEditing(null); }}>
          <Plus className="h-4 w-4 mr-2" /> Add Field
        </Button>
      </div>

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        <Button variant={filterEntity === "" ? "default" : "outline"} size="sm" onClick={() => setFilterEntity("")}>
          All
        </Button>
        {ENTITY_TYPES.map((et) => (
          <Button
            key={et}
            variant={filterEntity === et ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterEntity(et)}
          >
            {et.charAt(0).toUpperCase() + et.slice(1).replace("_", " ")}s
          </Button>
        ))}
      </div>

      {/* Create / Edit form */}
      {(creating || editing) && (
        <FieldForm
          initial={editing}
          onSave={() => { setCreating(false); setEditing(null); }}
          onCancel={() => { setCreating(false); setEditing(null); }}
        />
      )}

      {/* List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Field Definitions ({definitions.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : definitions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No custom fields defined yet. Click "Add Field" to create one.</p>
          ) : (
            <div className="space-y-2">
              {definitions
                .sort((a, b) => a.sort_order - b.sort_order)
                .map((f) => (
                  <div key={f.id} className="flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors">
                    <GripVertical className="h-4 w-4 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{f.label}</span>
                        {f.required && <Badge variant="outline" className="text-xs">required</Badge>}
                        {!f.active && <Badge variant="outline" className="text-xs text-muted-foreground">inactive</Badge>}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className={entityColor(f.entity_type)}>
                          {f.entity_type}
                        </Badge>
                        <Badge variant="outline" className="text-xs">{f.field_type}</Badge>
                        <span className="text-xs text-muted-foreground">order: {f.sort_order}</span>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => { setEditing(f); setCreating(false); }}>
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(f.id, f.label)}>
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function FieldForm({
  initial,
  onSave,
  onCancel,
}: {
  initial: FieldDef | null;
  onSave: () => void;
  onCancel: () => void;
}) {
  const [entityType, setEntityType] = useState(initial?.entity_type || "customer");
  const [label, setLabel] = useState(initial?.label || "");
  const [fieldType, setFieldType] = useState(initial?.field_type || "text");
  const [optionsStr, setOptionsStr] = useState(() => {
    if (!initial?.options) return "";
    try { return JSON.parse(initial.options).join("\n"); } catch { return initial.options; }
  });
  const [sortOrder, setSortOrder] = useState(initial?.sort_order ?? 0);
  const [required, setRequired] = useState(initial?.required ?? false);
  const [active, setActive] = useState(initial?.active ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const createMutation = useMutation({
    mutationFn: (data: {
      entity_type: string;
      label: string;
      field_type: string;
      options: string[];
      sort_order: number;
      required: boolean;
      active: boolean;
    }) => api.customFields.definitions.create(data),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: {
      id: string;
      data: {
        label: string;
        field_type: string;
        options: string[];
        sort_order: number;
        required: boolean;
        active: boolean;
      };
    }) => api.customFields.definitions.update(id, data),
  });

  const handleSave = async () => {
    if (!label.trim()) { setError("Label is required"); return; }
    setSaving(true);
    setError("");
    try {
      const lines: string[] = optionsStr.trim() ? optionsStr.split("\n") : [];
      const options = lines.map((s) => s.trim()).filter(Boolean);
      const data = {
        entity_type: entityType,
        label: label.trim(),
        field_type: fieldType,
        options,
        sort_order: sortOrder,
        required,
        active,
      };
      if (initial) {
        await updateMutation.mutateAsync({ id: initial.id, data });
      } else {
        await createMutation.mutateAsync(data);
      }
      queryClient.invalidateQueries({ queryKey: ["custom-fields"] });
      onSave();
    } catch (e: any) {
      setError(e?.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="border-primary/30">
      <CardHeader>
        <CardTitle className="text-sm flex items-center justify-between">
          <span>{initial ? `Edit: ${initial.label}` : "New Custom Field"}</span>
          <Button variant="ghost" size="sm" onClick={onCancel}>
            <X className="h-4 w-4" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <Label>Entity Type</Label>
            <select
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
            >
              {ENTITY_TYPES.map((et) => (
                <option key={et} value={et}>{et.charAt(0).toUpperCase() + et.slice(1).replace("_", " ")}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <Label>Field Type</Label>
            <select
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
              value={fieldType}
              onChange={(e) => setFieldType(e.target.value)}
            >
              {FIELD_TYPES.map((ft) => (
                <option key={ft} value={ft}>{ft}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="space-y-1">
          <Label>Label</Label>
          <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Serial Number" />
        </div>

        {(fieldType === "select" || fieldType === "multiselect") && (
          <div className="space-y-1">
            <Label>Options (one per line)</Label>
            <textarea
              className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={optionsStr}
              onChange={(e) => setOptionsStr(e.target.value)}
              placeholder="Option A&#10;Option B&#10;Option C"
            />
          </div>
        )}

        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-1">
            <Label>Sort Order</Label>
            <Input
              type="number"
              value={sortOrder}
              onChange={(e) => setSortOrder(parseInt(e.target.value) || 0)}
            />
          </div>
          <div className="flex items-center gap-2 pt-5">
            <input
              type="checkbox"
              id="cf-required"
              checked={required}
              onChange={(e) => setRequired(e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="cf-required">Required</Label>
          </div>
          <div className="flex items-center gap-2 pt-5">
            <input
              type="checkbox"
              id="cf-active"
              checked={active}
              onChange={(e) => setActive(e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="cf-active">Active</Label>
          </div>
        </div>

        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />{saving ? "Saving..." : "Save"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
