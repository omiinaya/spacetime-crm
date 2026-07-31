import { useState, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, Customer } from "../lib/api";
import type { Ticket as TicketType, Invoice, Appointment } from "../lib/api";
import { usePagination } from "../lib/usePagination";
import { queryClient } from "../lib/query-client";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import Pagination from "../components/Pagination";
import {
	Users,
	Plus,
	Search,
	Mail,
	Phone,
	MapPin,
	Edit2,
	Trash2,
	Key,
	Ticket as TicketIcon,
	Receipt,
	Calendar,
	ChevronDown,
	ChevronUp,
	Copy,
	AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

const PAGE_SIZE = 25;

const emptyForm: Partial<Customer> = {
	first_name: "",
	last_name: "",
	email: "",
	phone: "",
	mobile: "",
	address_line1: "",
	address_line2: "",
	city: "",
	state: "",
	zip: "",
	company: "",
	notes: "",
	tags: "",
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

interface TimelineEvent {
	id: string;
	ts: number;
	kind: "ticket" | "invoice" | "appointment";
	label: string;
	status: string;
	detail: string;
	page: string;
}

function CustomerDetailPanel({
	customer,
	onClose,
	onNavigate,
}: {
	customer: Customer;
	onClose: () => void;
	onNavigate?: (page: string) => void;
}) {
	const {
		data: ticketsData,
		isLoading: ticketsLoading,
	} = useQuery({
		queryKey: ["customer-tickets", customer.id],
		queryFn: () =>
			api.tickets.list("", customer.id, 0, 5) as Promise<{
				tickets: TicketType[];
				total: number;
			}>,
	});

	const {
		data: invoicesData,
		isLoading: invoicesLoading,
	} = useQuery({
		queryKey: ["customer-invoices", customer.id],
		queryFn: () =>
			api.invoices.list("", customer.id, 0, 5) as Promise<{
				invoices: Invoice[];
				total: number;
			}>,
	});

	const {
		data: appointmentsData,
		isLoading: appointmentsLoading,
	} = useQuery({
		queryKey: ["customer-appointments", customer.id],
		queryFn: () =>
			api.appointments.list(customer.id, 0, 5) as Promise<{
				appointments: Appointment[];
				total: number;
			}>,
	});

	const tickets = ticketsData?.tickets ?? [];
	const invoices = invoicesData?.invoices ?? [];
	const appointments = appointmentsData?.appointments ?? [];
	const loading = ticketsLoading || invoicesLoading || appointmentsLoading;

	const formatDate = (ts: number) => {
		if (!ts) return "—";
		return new Date(ts).toLocaleDateString("en-US", {
			month: "short",
			day: "numeric",
			year: "numeric",
		});
	};

	const formatDateTime = (ts: number) => {
		if (!ts) return "—";
		return new Date(ts).toLocaleString("en-US", {
			month: "short",
			day: "numeric",
			hour: "numeric",
			minute: "2-digit",
		});
	};

	const formatCurrency = (val: number, currency?: string) => {
		const sym =
			currency === "EUR" ? "\u20ac" : currency === "GBP" ? "\u00a3" : "$";
		return `${sym}${val.toFixed(2)}`;
	};

	// Merge tickets (created_at), invoices (created_at), and appointments
	// (start_time) into one chronological timeline, newest first.
	const events: TimelineEvent[] = [
		...tickets.map((t) => ({
			id: `ticket-${t.id}`,
			ts: t.created_at,
			kind: "ticket" as const,
			label: `#${t.ticket_number} ${t.title || "Untitled"}`,
			status: t.status,
			detail: formatDate(t.created_at),
			page: "tickets",
		})),
		...invoices.map((inv) => ({
			id: `invoice-${inv.id}`,
			ts: inv.created_at,
			kind: "invoice" as const,
			label: `Invoice #${inv.invoice_number}`,
			status: inv.status,
			detail: `${formatCurrency(inv.total, inv.currency)} · ${formatDate(
				inv.created_at,
			)}`,
			page: "invoices",
		})),
		...appointments.map((a) => ({
			id: `appointment-${a.id}`,
			ts: a.start_time,
			kind: "appointment" as const,
			label: a.title || "Appointment",
			status: a.status,
			detail: formatDateTime(a.start_time),
			page: "appointments",
		})),
	].sort((a, b) => b.ts - a.ts);

	const KIND_META = {
		ticket: { icon: TicketIcon, bg: "bg-blue-500/15 text-blue-400" },
		invoice: { icon: Receipt, bg: "bg-green-500/15 text-green-400" },
		appointment: { icon: Calendar, bg: "bg-purple-500/15 text-purple-400" },
	} as const;

	return (
		<div className="col-span-full border border-primary/20 rounded-lg bg-muted/30 p-4 animate-in slide-in-from-top-2 duration-200">
			<div className="flex items-start justify-between mb-4">
				<div>
					<h3 className="font-semibold text-lg">
						{customer.first_name} {customer.last_name}
					</h3>
					<p className="text-sm text-muted-foreground">
						{customer.email && <>{customer.email} &middot; </>}
						{customer.phone || customer.mobile}
					</p>
					{customer.company && (
						<p className="text-xs text-muted-foreground">{customer.company}</p>
					)}
				</div>
				<Button variant="ghost" size="sm" onClick={onClose}>
					<ChevronUp className="h-4 w-4" />
				</Button>
			</div>

			{/* Unified chronological activity timeline */}
			<Card>
				<CardHeader className="py-2 px-3">
					<CardTitle className="text-sm font-medium flex items-center gap-1.5">
						<Calendar className="h-3.5 w-3.5" /> Activity Timeline
						<span className="text-muted-foreground font-normal">
							({tickets.length} tickets · {invoices.length} invoices ·{" "}
							{appointments.length} appointments)
						</span>
					</CardTitle>
				</CardHeader>
				<CardContent className="py-2 px-3">
					{loading ? (
						<p className="text-xs text-muted-foreground py-3">
							Loading activity…
						</p>
					) : events.length === 0 ? (
						<p className="text-xs text-muted-foreground py-3">
							No activity yet — tickets, invoices, and appointments will
							appear here.
						</p>
					) : (
						<div>
							{events.map((ev, i) => {
								const meta = KIND_META[ev.kind];
								const Icon = meta.icon;
								return (
									<div key={ev.id} className="flex gap-3">
										{/* Icon + connector line */}
										<div className="flex flex-col items-center">
											<div
												className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${meta.bg}`}
											>
												<Icon className="h-3.5 w-3.5" />
											</div>
											{i < events.length - 1 && (
												<div className="w-px flex-1 bg-border" />
											)}
										</div>
										{/* Event content — click navigates to entity page */}
										<button
											type="button"
											className="flex-1 min-w-0 text-left py-1 pb-3 group"
											onClick={() => onNavigate?.(ev.page)}
											title={`Open ${ev.kind} — ${ev.label}`}
										>
											<div className="flex items-center gap-2">
												<span
													className={`w-1.5 h-1.5 rounded-full shrink-0 ${
														STATUS_COLORS[ev.status] || "bg-zinc-400"
													}`}
												/>
												<span className="text-xs font-medium truncate group-hover:text-primary transition-colors">
													{ev.label}
												</span>
												<span className="text-[10px] text-muted-foreground shrink-0 ml-auto">
													{ev.detail}
												</span>
											</div>
											<Badge
												variant="outline"
												className="text-[10px] px-1 py-0 h-4 mt-1 ml-3.5"
											>
												{ev.status.replace(/_/g, " ")}
											</Badge>
										</button>
									</div>
								);
							})}
						</div>
					)}
				</CardContent>
			</Card>
		</div>
	);
}

export default function CustomersPage({
	onNavigate,
}: {
	onNavigate?: (page: string) => void;
}) {
	const pag = usePagination(PAGE_SIZE);
	const [search, setSearch] = useState("");
	const [showForm, setShowForm] = useState(false);
	const [editId, setEditId] = useState<string | null>(null);
	const [form, setForm] = useState<Partial<Customer>>({ ...emptyForm });
	const [pwCustomer, setPwCustomer] = useState<Customer | null>(null);
	const [pwPassword, setPwPassword] = useState("");
	const [pwLoading, setPwLoading] = useState(false);
	const [expandedCustomerId, setExpandedCustomerId] = useState<string | null>(
		null,
	);

	const { data, isLoading } = useQuery({
		queryKey: ["customers", { search, offset: pag.offset }],
		queryFn: async () => {
			const res = await api.customers.list(search, pag.offset, PAGE_SIZE);
			pag.setTotal(res.total);
			return res.customers;
		},
	});

	const customers = data ?? [];
	const loading = isLoading;

	// ── Duplicate detection ──
	interface DuplicateGroup {
		field: string;
		value: string;
		customers: Customer[];
	}
	const [showDuplicates, setShowDuplicates] = useState(false);
	const { data: dupData } = useQuery({
		queryKey: ["customer-duplicates"],
		queryFn: () => api.customers.duplicates(),
		enabled: !showForm, // Don't fetch while editing
	});
	const duplicateCount = dupData?.count ?? 0;
	const duplicateGroups: DuplicateGroup[] = dupData?.duplicates ?? [];

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
			editId ? api.customers.update(editId, form) : api.customers.create(form),
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
			toast.success(
				`Portal password set for ${pwCustomer.first_name} ${pwCustomer.last_name}`,
			);
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
					<h1 className="text-2xl font-bold flex items-center gap-3">
						Customers
						{duplicateCount > 0 && (
							<Badge
								variant="outline"
								className="cursor-pointer text-amber-400 border-amber-400/40 hover:bg-amber-500/10 text-xs gap-1"
								onClick={() => setShowDuplicates(true)}
							>
								<Copy className="h-3 w-3" />
								{duplicateCount} duplicate{duplicateCount !== 1 ? "s" : ""}{" "}
								found
							</Badge>
						)}
					</h1>
					<p className="text-sm text-muted-foreground mt-1">
						Manage your customer database
					</p>
				</div>
				<Button
					onClick={() => {
						setForm({ ...emptyForm });
						setEditId(null);
						setShowForm(true);
					}}
				>
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
							<Input
								placeholder="First Name"
								value={form.first_name}
								onChange={(e) =>
									setForm({ ...form, first_name: e.target.value })
								}
							/>
							<Input
								placeholder="Last Name"
								value={form.last_name}
								onChange={(e) =>
									setForm({ ...form, last_name: e.target.value })
								}
							/>
							<Input
								placeholder="Email"
								value={form.email}
								onChange={(e) => setForm({ ...form, email: e.target.value })}
							/>
							<Input
								placeholder="Phone"
								value={form.phone}
								onChange={(e) => setForm({ ...form, phone: e.target.value })}
							/>
							<Input
								placeholder="Mobile"
								value={form.mobile}
								onChange={(e) => setForm({ ...form, mobile: e.target.value })}
							/>
							<Input
								placeholder="Company"
								value={form.company}
								onChange={(e) => setForm({ ...form, company: e.target.value })}
							/>
							<Input
								placeholder="Address Line 1"
								value={form.address_line1}
								onChange={(e) =>
									setForm({ ...form, address_line1: e.target.value })
								}
								className="md:col-span-2"
							/>
							<div className="md:col-span-2 grid grid-cols-3 gap-2">
								<Input
									placeholder="City"
									value={form.city}
									onChange={(e) => setForm({ ...form, city: e.target.value })}
								/>
								<Input
									placeholder="State"
									value={form.state}
									onChange={(e) => setForm({ ...form, state: e.target.value })}
								/>
								<Input
									placeholder="ZIP"
									value={form.zip}
									onChange={(e) => setForm({ ...form, zip: e.target.value })}
								/>
							</div>
							<Input
								placeholder="Tags (comma separated)"
								value={form.tags}
								onChange={(e) => setForm({ ...form, tags: e.target.value })}
								className="md:col-span-2"
							/>
							<Input
								placeholder="Notes"
								value={form.notes}
								onChange={(e) => setForm({ ...form, notes: e.target.value })}
								className="md:col-span-2"
							/>
						</div>
						<div className="flex gap-2 mt-4">
							<Button onClick={() => saveMutation.mutate()}>
								{editId ? "Update" : "Create"}
							</Button>
							<Button
								variant="outline"
								onClick={() => {
									setShowForm(false);
									setEditId(null);
								}}
							>
								Cancel
							</Button>
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
												<p className="text-xs text-muted-foreground truncate">
													{c.company}
												</p>
											)}
										</div>
									</div>
									<div
										className="flex gap-1 shrink-0"
										onClick={(e) => e.stopPropagation()}
									>
										<Button
											size="icon"
											variant="ghost"
											onClick={() => openPwDialog(c)}
											title="Set Portal Password"
										>
											<Key className="h-3.5 w-3.5" />
										</Button>
										<Button
											size="icon"
											variant="ghost"
											onClick={() => handleEdit(c)}
											title="Edit customer"
										>
											<Edit2 className="h-3.5 w-3.5" />
										</Button>
										<Button
											size="icon"
											variant="ghost"
											onClick={() => deleteMutation.mutate(c.id)}
											title="Delete customer"
										>
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
											<MapPin className="h-3 w-3" />{" "}
											{[c.city, c.state].filter(Boolean).join(", ")}
										</div>
									)}
									<div className="flex items-center gap-2 text-primary/60">
										<ChevronDown
											className={`h-3 w-3 transition-transform ${
												expandedCustomerId === c.id ? "rotate-180" : ""
											}`}
										/>
										{expandedCustomerId === c.id
											? "Hide details"
											: "Show details"}
									</div>
								</div>
							</CardContent>
						</Card>

						{expandedCustomerId === c.id && (
							<CustomerDetailPanel
								customer={c}
								onClose={() => setExpandedCustomerId(null)}
								onNavigate={onNavigate}
							/>
						)}
					</div>
				))}
				{!loading && customers.length === 0 && (
					<div className="col-span-full text-center py-12 text-muted-foreground">
						<Users className="h-12 w-12 mx-auto mb-3 opacity-30" />
						<p>No customers yet</p>
						<Button
							variant="outline"
							className="mt-2"
							onClick={() => {
								setForm({ ...emptyForm });
								setShowForm(true);
							}}
						>
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
				<div
					className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
					onClick={() => setPwCustomer(null)}
				>
					<Card
						className="w-full max-w-sm"
						onClick={(e) => e.stopPropagation()}
					>
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
								onKeyDown={(e) =>
									e.key === "Enter" && handleSetPortalPassword()
								}
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

			{/* Duplicate Detection Dialog */}
			{showDuplicates && (
				<div
					className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
					onClick={() => setShowDuplicates(false)}
				>
					<Card
						className="w-full max-w-lg max-h-[80vh] overflow-y-auto"
						onClick={(e) => e.stopPropagation()}
					>
						<CardHeader>
							<CardTitle className="flex items-center gap-2">
								<Copy className="h-5 w-5 text-amber-400" />
								Duplicate Customers ({duplicateCount})
							</CardTitle>
							<p className="text-sm text-muted-foreground">
								Customers sharing the same email or phone number
							</p>
						</CardHeader>
						<CardContent className="space-y-4">
							{duplicateGroups.length === 0 ? (
								<p className="text-sm text-muted-foreground py-4 text-center">
									No duplicates found
								</p>
							) : (
								duplicateGroups.map((group, gi) => (
									<div key={gi} className="border rounded-lg p-3 space-y-2">
										<div className="flex items-center gap-2 text-xs font-medium">
											<AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
											<Badge
												variant="outline"
												className="text-[10px] uppercase"
											>
												{group.field}
											</Badge>
											<span className="text-muted-foreground">
												{group.value}
											</span>
											<Badge className="ml-auto text-[10px]">
												{group.customers.length} customers
											</Badge>
										</div>
										{group.customers.map((c) => (
											<div
												key={c.id}
												className="flex items-center justify-between text-xs py-1.5 px-2 rounded bg-muted/50"
											>
												<span>
													{c.first_name} {c.last_name}
												</span>
												<span className="text-muted-foreground">
													{c.phone || c.mobile || c.email}
												</span>
											</div>
										))}
									</div>
								))
							)}
							<Button
								variant="outline"
								className="w-full"
								onClick={() => setShowDuplicates(false)}
							>
								Close
							</Button>
						</CardContent>
					</Card>
				</div>
			)}
		</>
	);
}
