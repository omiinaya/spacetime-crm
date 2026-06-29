import { useState, useEffect } from "react";
import { api, Estimate, Customer, EstimateLineItem } from "../lib/api";
import { usePagination } from "../lib/usePagination";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import Pagination from "../components/Pagination";
import { FileCheck, Plus, Trash2, FileText } from "lucide-react";

const PAGE_SIZE = 25;
import { toast } from "sonner";

const statusColors: Record<string, "default" | "warning" | "success" | "destructive" | "outline"> = {
  draft: "outline",
  sent: "default",
  approved: "success",
  declined: "destructive",
};

export default function EstimatesPage() {
  const pag = usePagination(PAGE_SIZE);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ customer_id: "", ticket_id: "", notes: "", expires_at: "" });
  const [selectedEst, setSelectedEst] = useState<Estimate | null>(null);
  const [lineItems, setLineItems] = useState<EstimateLineItem[]>([]);
  const [newItem, setNewItem] = useState({ description: "", quantity: 1, unit_price: 0, item_type: "service" });

  const load = async (offset: number) => {
    try {
      const [eRes, cRes] = await Promise.all([api.estimates.list(filter, offset, PAGE_SIZE), api.customers.list()]);
      setEstimates(eRes.estimates);
      setCustomers(cRes.customers);
      pag.setTotal(eRes.total);
    } catch { toast.error("Failed to load estimates"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(pag.offset); }, [filter, pag.offset]);

  const handleCreate = async () => {
    try {
      await api.estimates.create({
        customer_id: form.customer_id, ticket_id: form.ticket_id,
        notes: form.notes, expires_at: form.expires_at ? new Date(form.expires_at).getTime() : 0,
      });
      toast.success("Estimate created");
      setShowForm(false);
      setForm({ customer_id: "", ticket_id: "", notes: "", expires_at: "" });
      load(pag.offset);
    } catch { toast.error("Failed to create estimate"); }
  };

  const selectEst = async (est: Estimate) => {
    setSelectedEst(est);
    try {
      const res = await api.estimates.lineItems.list(est.id);
      setLineItems(res.line_items);
    } catch { setLineItems([]); }
    setNewItem({ description: "", quantity: 1, unit_price: 0, item_type: "service" });
  };

  const addLineItem = async () => {
    if (!selectedEst) return;
    try {
      await api.estimates.lineItems.create(selectedEst.id, newItem);
      const res = await api.estimates.lineItems.list(selectedEst.id);
      setLineItems(res.line_items);
      setNewItem({ description: "", quantity: 1, unit_price: 0, item_type: "service" });
      load(pag.offset);
    } catch { toast.error("Failed to add item"); }
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Estimates</h1>
          <p className="text-sm text-muted-foreground mt-1">Create and manage estimates</p>
        </div>
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-1.5" />New Estimate</Button>
      </div>

      <div className="flex gap-2 flex-wrap">
        {["", "draft", "sent", "approved", "declined"].map((s) => (
          <Button key={s} size="sm" variant={filter === s ? "default" : "outline"} onClick={() => { setFilter(s); pag.reset(); }}>{s || "All"}</Button>
        ))}
      </div>

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader><CardTitle>New Estimate</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })}>
              <option value="">Select customer...</option>
              {customers.map((c) => (<option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>))}
            </Select>
            <Input placeholder="Ticket ID (optional)" value={form.ticket_id} onChange={(e) => setForm({ ...form, ticket_id: e.target.value })} />
            <Input placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            <Input type="date" placeholder="Expires" value={form.expires_at} onChange={(e) => setForm({ ...form, expires_at: e.target.value })} />
            <div className="flex gap-2">
              <Button onClick={handleCreate}>Create</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-3">
          {estimates.map((est) => {
            const cust = customers.find((c) => c.id === est.customer_id);
            return (
              <Card key={est.id} className={`cursor-pointer ${selectedEst?.id === est.id ? "border-primary" : "hover:border-primary/30"}`} onClick={() => selectEst(est)}>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">#{est.estimate_number}</span>
                    <Badge variant={statusColors[est.status] || "outline"}>{est.status}</Badge>
                  </div>
                  <p className="font-medium mt-1">${est.total.toFixed(2)}</p>
                  {cust && <p className="text-xs text-muted-foreground">{cust.first_name} {cust.last_name}</p>}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {selectedEst && (
          <div className="space-y-4">
            <Card>
              <CardHeader><CardTitle>#{selectedEst.estimate_number} — ${selectedEst.total.toFixed(2)}</CardTitle>
                {selectedEst.status === "approved" && (
                  <Button size="sm" variant="default" onClick={async () => {
                    try {
                      await api.estimates.convert(selectedEst.id);
                      toast.success("Converted to invoice!");
                      setSelectedEst(null);
                      load(pag.offset);
                    } catch { toast.error("Failed to convert"); }
                  }}>
                    <FileText className="h-3.5 w-3.5 mr-1" /> Convert to Invoice
                  </Button>
                )}
              </CardHeader>
              <CardContent className="space-y-3">
                <Select value={selectedEst.status} onChange={(e) => { api.estimates.updateStatus(selectedEst.id, e.target.value); selectEst(selectedEst); }}>
                  <option value="draft">Draft</option>
                  <option value="sent">Sent</option>
                  <option value="approved">Approved</option>
                  <option value="declined">Declined</option>
                </Select>
                <div className="space-y-2">
                  {lineItems.map((li) => (
                    <div key={li.id} className="flex justify-between text-sm p-2 rounded bg-muted/50">
                      <div><p className="truncate">{li.description}</p><p className="text-xs text-muted-foreground">{li.quantity} x ${li.unit_price.toFixed(2)}</p></div>
                      <span className="font-medium shrink-0">${li.total.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Select value={newItem.item_type} onChange={(e) => setNewItem({ ...newItem, item_type: e.target.value })} className="w-24">
                    <option value="service">Service</option>
                    <option value="part">Part</option>
                  </Select>
                  <Input placeholder="Description" value={newItem.description} onChange={(e) => setNewItem({ ...newItem, description: e.target.value })} />
                  <Input type="number" placeholder="Qty" value={newItem.quantity} onChange={(e) => setNewItem({ ...newItem, quantity: +e.target.value })} className="w-20" />
                  <Input type="number" placeholder="Price" value={newItem.unit_price} onChange={(e) => setNewItem({ ...newItem, unit_price: +e.target.value })} className="w-24" />
                  <Button size="sm" onClick={addLineItem}><Plus className="h-3 w-3" /></Button>
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
