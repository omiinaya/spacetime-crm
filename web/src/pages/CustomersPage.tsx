import { useState, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, Customer } from "../lib/api";
import type { Ticket as TicketType, Invoice } from "../lib/api";
import { usePagination } from "../lib/usePagination";
import { queryClient } from "../lib/query-client";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import Pagination from "../components/Pagination";
import {
  Users, Plus, Search, Mail, Phone, MapPin, Edit2, Trash2, Key,
  Ticket as TicketIcon, Receipt, ChevronDown, ChevronUp,
} from "lucide-react";
import { toast } from "sonner";

const PAGE_SIZE = 25;

const emptyForm: Partial<Customer> = {
  first_name: "", last_name: "", email: "", phone: "", mobile: "",
  address_line1: "", address_line2: "", city: "", state: "", zip: "",
  company: "", notes: "", tags: "",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-zinc-500",
  sent: "bg-blue-500",
  paid: "bg-green-500",
  overdue: "bg-red-500",
  partial: "bg-amber-500",
  cancelled: "bg-zinc-300",
  new: "bg-blue-500",
  in_progress: "bg-amber-500",
  waiting_parts: "bg-purple-500",
  waiting_customer: "bg-orange-500",
  resolved: "bg-green-500",
  closed: "bg-zinc-400",
  scheduled: "bg-blue-500",
  completed: "bg-green-500",
  no_show: "bg-red-500",
  pending_approval: "bg-amber-500",
  approved: "bg-green-500",
};

function CustomerDetailPanel({
  customer,
  onClose,
}: {
  customer: Customer;
  onClose: () => void;
}) {
  const { data: ticketsData } = useQuery({
    queryKey: ["customer-tickets", customer.id],
    queryFn: () =>
      api.tickets.list("", customer.id, 0, 5) as Promise<{
        tickets: TicketType[];
        total: number;
      }>,
  });

  const { data: invoicesData } = useQuery({
    queryKey: ["customer-invoices", customer.id],
    queryFn: () =>
      api.invoices.list("", customer.id, 0, 5) as Promise<{
        invoices: Invoice[];
        total: number;
      }>,
  });

  const tickets = ticketsData?.tickets ?? [];
  const invoices = invoicesData?.invoices ?? [];

  const formatDate = (ts: number) => {
    if (!ts) return "—";
    const d = new Date(ts);
    return d.toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
    });
  };

  const formatCurrency = (val: number, currency?: string) => {
    const sym = currency === "EUR" ? "\u20ac" : currency === "GBP" ? "\u00a3" : "$";
    return `${sym}${val.toFixed(2)}`;
  };

  return (
    <div className="col-span-full border border-primary/20 rounded-lg bg-muted/30 p-4 animate-in slide-in-from-top-2 duration-200">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-lg">{customer.first_name} {customer.last_name}</h3>
          <p className="text-sm text-muted-foreground">
            {customer.email && <>{customer.email} &middot; </>}
            {customer.phone || customer.mobile}
          </p>
          {customer.company && <p className="text-xs text-muted-foreground">{customer.company}</p>}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <ChevronUp className="h-4 w-4" />
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Recent Tickets */}
        <Card>
          <CardHeader className="py-2 px-3">
            <CardTitle className="text-sm font-medium flex items-center gap-1.5">
              <TicketIcon className="h-3.5 w-3.5" /> Recent Tickets ({tickets.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="py-1 px-3">
            {tickets.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No tickets</p>
            ) : (
              <div className="space-y-1.5">
                {tickets.map((t) => (
                  <div key={t.id} className="flex items-center justify-between text-xs py-1">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_COLORS[t.status] || "bg-zinc-400"}`} />
                      <span className="truncate">#{t.ticket_number} {t.title}</span>
                    </div>
                    <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 shrink-0">
                      {t.status.replace(/_/g, " ")}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Invoices */}
        <Card>
          <CardHeader className="py-2 px-3">
            <CardTitle className="text-sm font-medium flex items-center gap-1.5">
              <Receipt className="h-3.5 w-3.5" /> Recent Invoices ({invoices.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="py-1 px-3">
            {invoices.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No invoices</p>
            ) : (
              <div className="space-y-1.5">
                {invoices.map((inv) => (
                  <div key={inv.id} className="flex items-center justify-between text-xs py-1">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_COLORS[inv.status] || "bg-zinc-400"}`} />
                      <span className="truncate">#{inv.invoice_number} — {formatDate(inv.created_at)}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="font-medium">{formatCurrency(inv.total, inv.currency)}</span>
                      <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">
                        {inv.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function CustomersPage() {
  const pag = usePagination(PAGE_SIZE);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<Customer>>({ ...emptyForm });
  const [pwCustomer, setPwCustomer] = useState<Customer | null>(null);
  const [pwPassword, setPwPassword] = useState("");
  const [pwLoading, setPwLoading] = useState(false);
  const [expandedCustomerId, setExpandedCustomerId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["customers", { search, offset: pag.offset }],
    queryFn: () => api.customers.list(search, pag.offset, PAGE_SIZE),
    select: (res) => {
      pag.setTotal(res.total);
      return res.customers;
    },
  });

  const customers = data ?? [];
  const loading = isLoading;

  // Reset to page 1 when search changes
  const handleSearch = (val: string) => {
    setSearch(val);
    pag.reset();
  };

  const handleToggleExpand = useCallback((cid: string) => {
    setExpandedCustomerId((prev) => (prev === cid ? null : cid));
  }, []);

  const saveMutation = useMutation({
    mutationFn: () =>
      editId
        ? api.customers.update(editId, form)
        : api.customers.create(form),
    onSuccess: () => {
      toast.success(editId ? "Customer updated" : "Customer created");
      setShowForm(false);
      setEditId(null);
      setForm({ ...emptyForm });
      queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: () => {
      toast.error("Failed to save customer");
    },
  });

  const handleEdit = (c: Customer) => {
    setForm(c);
    setEditId(c.id);
    setShowForm(true);
  };

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.customers.delete(id),
    onSuccess: () => {
      toast.success("Customer deleted");
      queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: () => {
      toast.error("Failed to delete");
    },
  });

  const openPwDialog = (c: Customer) => {
    setPwCustomer(c);
    setPwPassword("");
  };

  const handleSetPortalPassword = async () => {
    if (!pwCustomer || pwPassword.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }
    setPwLoading(true);
    try {
      await api.customers.setPortalPassword(pwCustomer.id, pwPassword);
      toast.success(`Portal password set for ${pwCustomer.first_name} ${pwCustomer.last_name}`);
      setPwCustomer(null);
      setPwPassword("");
    } catch {
      toast.error("Failed to set portal password");
    } finally {
      setPwLoading(false);
    }
  };

  const fullName = (c: Customer) => `${c.first_name} ${c.last_name}`;

  return (
    <>
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Customers</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your customer database
          </p>
        </div>
        <Button onClick={() => { setForm({ ...emptyForm }); setEditId(null); setShowForm(true); }}>
          <Plus className="h-4 w-4 mr-1.5" /> Add Customer
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-full sm:max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search customers..."
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Form modal */}
      {showForm && (
        <Card className="border-primary/30">
          <CardHeader>
            <CardTitle>{editId ? "Edit Customer" : "New Customer"}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input placeholder="First Name" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
              <Input placeholder="Last Name" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
              <Input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              <Input placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              <Input placeholder="Mobile" value={form.mobile} onChange={(e) => setForm({ ...form, mobile: e.target.value })} />
              <Input placeholder="Company" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
              <Input placeholder="Address Line 1" value={form.address_line1} onChange={(e) => setForm({ ...form, address_line1: e.target.value })} className="md:col-span-2" />
              <div className="md:col-span-2 grid grid-cols-3 gap-2">
                <Input placeholder="City" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
                <Input placeholder="State" value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} />
                <Input placeholder="ZIP" value={form.zip} onChange={(e) => setForm({ ...form, zip: e.target.value })} />
              </div>
              <Input placeholder="Tags (comma separated)" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} className="md:col-span-2" />
              <Input placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="md:col-span-2" />
            </div>
            <div className="flex gap-2 mt-4">
              <Button onClick={() => saveMutation.mutate()}>{editId ? "Update" : "Create"}</Button>
              <Button variant="outline" onClick={() => { setShowForm(false); setEditId(null); }}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Customer list */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {customers.map((c) => (
          <div key={c.id} className="contents">
            <Card
              className={`hover:border-primary/30 transition-colors cursor-pointer ${
                expandedCustomerId === c.id ? "border-primary/40" : ""
              }`}
              onClick={() => handleToggleExpand(c.id)}
            >
              <CardContent className="pt-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      <Users className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium truncate">{fullName(c)}</p>
                      {c.company && (
                        <p className="text-xs text-muted-foreground truncate">{c.company}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <Button size="icon" variant="ghost" onClick={() => openPwDialog(c)} title="Set Portal Password">
                      <Key className="h-3.5 w-3.5" />
                    </Button>
                    <Button size="icon" variant="ghost" onClick={() => handleEdit(c)}>
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>
                    <Button size="icon" variant="ghost" onClick={() => deleteMutation.mutate(c.id)}>
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </div>
                </div>
                <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                  {c.email && (
                    <div className="flex items-center gap-2">
                      <Mail className="h-3 w-3" /> {c.email}
                    </div>
                  )}
                  {c.phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="h-3 w-3" /> {c.phone}
                    </div>
                  )}
                  {(c.city || c.state) && (
                    <div className="flex items-center gap-2">
                      <MapPin className="h-3 w-3" /> {[c.city, c.state].filter(Boolean).join(", ")}
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-primary/60">
                    <ChevronDown className={`h-3 w-3 transition-transform ${
                      expandedCustomerId === c.id ? "rotate-180" : ""
                    }`} />
                    {expandedCustomerId === c.id ? "Hide details" : "Show details"}
                  </div>
                </div>
              </CardContent>
            </Card>

            {expandedCustomerId === c.id && (
              <CustomerDetailPanel customer={c} onClose={() => setExpandedCustomerId(null)} />
            )}
          </div>
        ))}
        {!loading && customers.length === 0 && (
          <div className="col-span-full text-center py-12 text-muted-foreground">
            <Users className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p>No customers yet</p>
            <Button variant="outline" className="mt-2" onClick={() => { setForm({ ...emptyForm }); setShowForm(true); }}>
              <Plus className="h-4 w-4 mr-1" /> Add your first customer
            </Button>
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

      {/* Portal Password Dialog */}
      {pwCustomer && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={() => setPwCustomer(null)}>
          <Card className="w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <CardHeader>
              <CardTitle>Set Portal Password</CardTitle>
              <p className="text-sm text-muted-foreground">
                Set password for {pwCustomer.first_name} {pwCustomer.last_name}
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                type="password"
                placeholder="Min. 6 characters"
                value={pwPassword}
                onChange={(e) => setPwPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSetPortalPassword()}
              />
              <div className="flex gap-2">
                <Button onClick={handleSetPortalPassword} disabled={pwLoading}>
                  {pwLoading ? "Setting..." : "Set Password"}
                </Button>
                <Button variant="outline" onClick={() => setPwCustomer(null)}>
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
