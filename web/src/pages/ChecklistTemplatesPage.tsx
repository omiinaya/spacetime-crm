import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api, ChecklistTemplate, ChecklistItem } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { ListChecks, Plus, Pencil, Trash2, X } from "lucide-react";
import { toast } from "sonner";

interface TemplateEditorProps {
  template?: ChecklistTemplate;
  onSave: (name: string, description: string, items: ChecklistItem[]) => Promise<void>;
  onCancel: () => void;
}

function TemplateEditor({ template, onSave, onCancel }: TemplateEditorProps) {
  const [name, setName] = useState(template?.name ?? "");
  const [desc, setDesc] = useState(template?.description ?? "");
  const [items, setItems] = useState<ChecklistItem[]>(() => {
    if (template) {
      try { return JSON.parse(template.items); } catch { return []; }
    }
    return [{ label: "", sort_order: 0 }];
  });

  const addItem = () => setItems([...items, { label: "", sort_order: items.length }]);
  const removeItem = (i: number) => setItems(items.filter((_, idx) => idx !== i));
  const updateItem = (i: number, label: string) => {
    const next = [...items];
    next[i] = { ...next[i], label, sort_order: next[i]?.sort_order ?? i };
    setItems(next);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await onSave(name.trim(), desc.trim(), items.filter(i => i.label.trim()));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="text-sm font-medium mb-1 block">Template Name</label>
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          placeholder="e.g. Standard PC Repair"
          required
        />
      </div>
      <div>
        <label className="text-sm font-medium mb-1 block">Description (optional)</label>
        <input
          value={desc}
          onChange={e => setDesc(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          placeholder="Brief description of this template"
        />
      </div>
      <div>
        <label className="text-sm font-medium mb-1 block">Checklist Items</label>
        <div className="space-y-2">
          {items.map((item, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={item.label}
                onChange={e => updateItem(i, e.target.value)}
                className="flex-1 px-3 py-1.5 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder={`Item ${i + 1}`}
              />
              {items.length > 1 && (
                <button type="button" onClick={() => removeItem(i)} className="text-muted-foreground hover:text-destructive p-1">
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </div>
        <button type="button" onClick={addItem} className="text-xs text-primary hover:underline mt-2">
          + Add item
        </button>
      </div>
      <div className="flex gap-2 justify-end">
        <Button type="button" variant="outline" size="sm" onClick={onCancel}>Cancel</Button>
        <Button type="submit" size="sm" disabled={!name.trim()}>
          {template ? "Update" : "Create"} Template
        </Button>
      </div>
    </form>
  );
}

export default function ChecklistTemplatesPage() {
  const [editing, setEditing] = useState<ChecklistTemplate | null>(null);
  const [showEditor, setShowEditor] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["checklist-templates"],
    queryFn: async () => {
      const res = await api.checklist.templates.list();
      return res.templates;
    },
  });

  const templates = data ?? [];

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description: string; items: ChecklistItem[] }) =>
      api.checklist.templates.create(data),
    onSuccess: () => {
      toast.success("Template created");
      setShowEditor(false);
      queryClient.invalidateQueries({ queryKey: ["checklist-templates"] });
    },
    onError: () => toast.error("Failed to create template"),
  });

  const updateMutation = useMutation({
    mutationFn: (data: { id: string; name: string; description: string; items: ChecklistItem[] }) =>
      api.checklist.templates.update(data.id, { name: data.name, description: data.description, items: data.items }),
    onSuccess: () => {
      toast.success("Template updated");
      setEditing(null);
      queryClient.invalidateQueries({ queryKey: ["checklist-templates"] });
    },
    onError: () => toast.error("Failed to update template"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.checklist.templates.delete(id),
    onSuccess: () => {
      toast.success("Template deleted");
      queryClient.invalidateQueries({ queryKey: ["checklist-templates"] });
    },
    onError: () => toast.error("Failed to delete template"),
  });

  const handleCreate = async (name: string, desc: string, items: ChecklistItem[]) => {
    await createMutation.mutateAsync({ name, description: desc, items });
  };

  const handleUpdate = async (name: string, desc: string, items: ChecklistItem[]) => {
    if (!editing) return;
    await updateMutation.mutateAsync({ id: editing.id, name, description: desc, items });
  };

  const handleDelete = async (t: ChecklistTemplate) => {
    await deleteMutation.mutateAsync(t.id);
  };

  const parseItems = (t: ChecklistTemplate): ChecklistItem[] => {
    try { return JSON.parse(t.items); } catch { return []; }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ListChecks className="h-6 w-6 text-primary" />
            Checklist Templates
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create and manage repair checklist templates
          </p>
        </div>
        <Button onClick={() => { setEditing(null); setShowEditor(true); }}>
          <Plus className="h-4 w-4 mr-1" /> New Template
        </Button>
      </div>

      {/* Editor dialog */}
      {(showEditor || editing) && (
        <Card>
          <CardHeader><CardTitle className="text-sm">{editing ? "Edit Template" : "New Template"}</CardTitle></CardHeader>
          <CardContent>
            <TemplateEditor
              {...(editing ? { template: editing } : {})}
              onSave={editing ? handleUpdate : handleCreate}
              onCancel={() => { setShowEditor(false); setEditing(null); }}
            />
          </CardContent>
        </Card>
      )}

      {/* Templates list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      ) : templates.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <ListChecks className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No checklist templates yet</p>
          <p className="text-xs mt-1">Create templates to quickly apply standard checklists to tickets</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map(t => {
            const items = parseItems(t);
            const done = items.filter(i => i.label).length;
            return (
              <Card key={t.id} className="hover:border-primary/30 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="min-w-0">
                      <h3 className="font-medium text-sm truncate">{t.name}</h3>
                      {t.description && <p className="text-xs text-muted-foreground truncate mt-0.5">{t.description}</p>}
                    </div>
                    <div className="flex gap-1 shrink-0 ml-2">
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => { setEditing(t); setShowEditor(true); }}>
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive" onClick={() => handleDelete(t)}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-xs">{done} items</Badge>
                  {done > 0 && (
                    <div className="mt-2 space-y-1">
                      {items.filter(i => i.label).slice(0, 4).map((item, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
                          <div className="w-1 h-1 rounded-full bg-muted-foreground/50" />
                          <span className="truncate">{item.label}</span>
                        </div>
                      ))}
                      {done > 4 && <p className="text-xs text-muted-foreground mt-1">+{done - 4} more</p>}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
