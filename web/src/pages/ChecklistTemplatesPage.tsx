export default function ChecklistTemplatesPage() {
  const [templates, setTemplates] = useState<ChecklistTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<ChecklistTemplate | null>(null);
  const [showEditor, setShowEditor] = useState(false);

  const load = async () => {
    try {
      const res = await api.checklist.templates.list();
      setTemplates(res.templates);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (name: string, desc: string, items: ChecklistItem[]) => {
    await api.checklist.templates.create({ name, description: desc, items });
    toast.success("Template created");
    setShowEditor(false);
    load();
  };

  const handleUpdate = async (name: string, desc: string, items: ChecklistItem[]) => {
    if (!editing) return;
    await api.checklist.templates.update(editing.id, { name, description: desc, items });
    toast.success("Template updated");
    setEditing(null);
    load();
  };

  const handleDelete = async (t: ChecklistTemplate) => {
    await api.checklist.templates.delete(t.id);
    toast.success("Template deleted");
    load();
  };

  const parseItems = (t: ChecklistTemplate): ChecklistItem[] => {
    try { return JSON.parse(t.items); } catch { return []; }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
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
              template={editing || undefined}
              onSave={editing ? handleUpdate : handleCreate}
              onCancel={() => { setShowEditor(false); setEditing(null); }}
            />
          </CardContent>
        </Card>
      )}

      {/* Templates list */}
      {loading ? (
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
