import { useState, useEffect } from "react";
import { toast } from "sonner";
import { useMutation } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import {
	Users,
	Ticket,
	FileText,
	CreditCard,
	Calendar,
	Package,
	CheckCircle,
	ArrowRight,
	Loader2,
	type LucideIcon,
} from "lucide-react";
import { api, DashboardStats, ReportsData, Invoice } from "../lib/api";
import { Badge } from "../components/ui/badge";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
	BarChart,
	Bar,
	PieChart,
	Pie,
	Cell,
	XAxis,
	YAxis,
	CartesianGrid,
	Tooltip,
	ResponsiveContainer,
} from "recharts";

const STATUS_COLORS = [
	"#22c55e",
	"#eab308",
	"#ef4444",
	"#3b82f6",
	"#a855f7",
	"#ec4899",
	"#6366f1",
];

type PageId =
	| "dashboard"
	| "customers"
	| "tickets"
	| "invoices"
	| "payments"
	| "appointments"
	| "products"
	| "estimates"
	| "purchase-orders"
	| "import-export"
	| "audit-log"
	| "pos"
	| "health"
	| "custom-fields"
	| "checklist"
	| "map"
	| "reports"
	| "settings"
	| "tenants"
	| "recurring-invoices"
	| "payment-methods";

export default function DashboardPage({
	stats,
	onNavigate,
}: {
	stats: DashboardStats | null;
	onNavigate: (p: PageId) => void;
}) {
	const [reports, setReports] = useState<ReportsData | null>(null);

	const updateApptStatus = useMutation({
		mutationFn: async ({ id, status }: { id: string; status: string }) =>
			api.appointments.updateStatus(id, status),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
		},
		onError: () => toast.error("Failed to update appointment status"),
	});

	const markPaid = useMutation({
		mutationFn: async (inv: Invoice) =>
			api.payments.record({
				invoice_id: inv.id,
				customer_id: inv.customer_id,
				amount: Number(inv.total),
				method: "cash",
				currency: inv.currency || "USD",
				notes: "Marked paid from dashboard",
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
		},
		onError: () => toast.error("Failed to mark invoice as paid"),
	});

	const claimTicket = useMutation({
		mutationFn: async (ticketId: string) => {
			const user = JSON.parse(localStorage.getItem("user") || "{}");
			return api.tickets.assign(ticketId, user.id || "");
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
		},
		onError: () => toast.error("Failed to claim ticket"),
	});

	useEffect(() => {
		api.reports
			.get()
			.then(setReports)
			.catch(() => toast.error("Failed to load reports data"));
	}, []);

	const summaryCards: {
		label: string;
		value: string | number;
		icon: LucideIcon;
		color: string;
		link: PageId;
	}[] = [
		{
			label: "Total Customers",
			value: stats?.total_customers ?? 0,
			icon: Users,
			color: "text-blue-400",
			link: "customers",
		},
		{
			label: "Open Tickets",
			value: stats?.open_tickets ?? 0,
			icon: Ticket,
			color: "text-amber-400",
			link: "tickets",
		},
		{
			label: "Revenue",
			value: `$${(stats?.revenue ?? 0).toFixed(2)}`,
			icon: CreditCard,
			color: "text-green-400",
			link: "invoices",
		},
		{
			label: "Upcoming Appointments",
			value: stats?.upcoming_appointments ?? 0,
			icon: Calendar,
			color: "text-purple-400",
			link: "appointments",
		},
		...(stats
			? [
					{
						label: "Avg Resolution",
						value: `${stats.avg_resolution_hours}h`,
						icon: CheckCircle,
						color: "text-sky-400",
						link: "tickets" as PageId,
					},
				]
			: []),
	];

	return (
		<>
			<div>
				<h1 className="text-2xl font-bold">Dashboard</h1>
				<p className="text-sm text-muted-foreground mt-1">
					Overview of your repair business
				</p>
			</div>

			{/* Summary cards */}
			<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
				{summaryCards.map((card) => {
					const Icon = card.icon;
					return (
						<Card
							key={card.label}
							className="cursor-pointer hover:bg-[var(--color-card)]/80 transition-colors"
							onClick={() => onNavigate(card.link)}
						>
							<CardContent className="flex items-center gap-4 pt-4">
								<div className="p-2 rounded-lg bg-muted">
									<Icon className={`h-5 w-5 ${card.color}`} />
								</div>
								<div className="flex-1 min-w-0">
									<p className="text-xs text-muted-foreground">{card.label}</p>
									<p className="text-xl font-bold">{card.value}</p>
								</div>
							</CardContent>
						</Card>
					);
				})}
			</div>

			{/* Revenue vs Target progress bar */}
			{stats && (
				<Card>
					<CardContent className="pt-4">
						<div className="flex items-center justify-between mb-2">
							<span className="text-sm font-medium">
								Monthly Revenue Target
							</span>
							<span className="text-sm text-muted-foreground">
								${Number(stats.monthly_revenue ?? 0).toFixed(2)} / $
								{Number(stats.revenue_target ?? 0).toFixed(2)}
							</span>
						</div>
						<div className="h-3 bg-muted rounded-full overflow-hidden">
							<div
								className={`h-full rounded-full transition-all duration-500 ${(() => {
									const ratio =
										Number(stats.monthly_revenue ?? 0) /
										Number(stats.revenue_target ?? 0);
									if (ratio >= 1) return "bg-green-500";
									if (ratio >= 0.75) return "bg-blue-500";
									if (ratio >= 0.5) return "bg-amber-500";
									return "bg-red-500";
								})()}`}
								style={{
									width: `${Math.min(
										(Number(stats.monthly_revenue ?? 0) /
											Number(stats.revenue_target ?? 0)) *
											100,
										100,
									)}%`,
								}}
							/>
						</div>
						<p className="text-xs text-muted-foreground mt-1">
							{(() => {
								const target = Number(stats.revenue_target ?? 0);
								if (target <= 0) return "0% of monthly target";
								return `${Math.min((Number(stats.monthly_revenue ?? 0) / target) * 100, 100).toFixed(0)}% of monthly target`;
							})()}
						</p>
					</CardContent>
				</Card>
			)}

			{/* Quick actions */}
			<Card>
				<CardHeader>
					<CardTitle>Quick Actions</CardTitle>
				</CardHeader>
				<CardContent className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
					{[
						{ label: "New Customer", page: "customers" as PageId, icon: Users },
						{ label: "New Ticket", page: "tickets" as PageId, icon: Ticket },
						{
							label: "New Invoice",
							page: "invoices" as PageId,
							icon: FileText,
						},
						{
							label: "New Appointment",
							page: "appointments" as PageId,
							icon: Calendar,
						},
						{ label: "Add Product", page: "products" as PageId, icon: Package },
					].map((action) => {
						const Icon = action.icon;
						return (
							<Button
								key={action.label}
								variant="outline"
								className="h-20 flex-col gap-2"
								onClick={() => onNavigate(action.page)}
							>
								<Icon className="h-5 w-5" />
								<span className="text-xs">{action.label}</span>
							</Button>
						);
					})}
				</CardContent>
			</Card>

			{/* Charts row */}
			<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
				<Card>
					<CardHeader>
						<CardTitle>Monthly Revenue</CardTitle>
					</CardHeader>
					<CardContent className="h-64">
						{reports && reports.revenue_by_month.length > 0 ? (
							<ResponsiveContainer width="100%" height="100%">
								<BarChart
									data={reports.revenue_by_month}
									margin={{ top: 5, right: 5, left: 0, bottom: 20 }}
								>
									<CartesianGrid
										strokeDasharray="3 3"
										stroke="var(--color-border)"
									/>
									<XAxis
										dataKey="month"
										tick={{ fontSize: 11 }}
										stroke="var(--color-muted-foreground)"
									/>
									<YAxis
										tick={{ fontSize: 11 }}
										stroke="var(--color-muted-foreground)"
										tickFormatter={(v) => `$${v}`}
									/>
									<Tooltip
										contentStyle={{
											background: "var(--color-card)",
											border: "1px solid var(--color-border)",
											borderRadius: "8px",
										}}
										formatter={(v: any) => [
											`$${Number(v || 0).toFixed(2)}`,
											"Revenue",
										]}
									/>
									<Bar
										dataKey="revenue"
										fill="var(--color-primary)"
										radius={[4, 4, 0, 0]}
									/>
								</BarChart>
							</ResponsiveContainer>
						) : (
							<div className="flex items-center justify-center h-full text-muted-foreground text-sm">
								No revenue data yet
							</div>
						)}
					</CardContent>
				</Card>

				<Card>
					<CardHeader>
						<CardTitle>Tickets by Status</CardTitle>
					</CardHeader>
					<CardContent className="h-64">
						{reports && reports.ticket_by_status.length > 0 ? (
							<ResponsiveContainer width="100%" height="100%">
								<PieChart>
									<Pie
										data={reports.ticket_by_status}
										dataKey="count"
										nameKey="status"
										cx="50%"
										cy="50%"
										outerRadius={80}
										label={(props: any) =>
											`${props?.status || props?.payload?.status || ""}: ${props?.count || props?.payload?.count || 0}`
										}
									>
										{reports.ticket_by_status.map((_, i) => (
											<Cell
												key={i}
												fill={STATUS_COLORS[i % STATUS_COLORS.length]}
											/>
										))}
									</Pie>
									<Tooltip
										contentStyle={{
											background: "var(--color-card)",
											border: "1px solid var(--color-border)",
											borderRadius: "8px",
										}}
									/>
								</PieChart>
							</ResponsiveContainer>
						) : (
							<div className="flex items-center justify-center h-full text-muted-foreground text-sm">
								No ticket data yet
							</div>
						)}
					</CardContent>
				</Card>
			</div>

			{/* Overdue Invoices Alert */}
			{(() => {
				const overdueCount = stats?.overdue_invoices_count;
				const overdueInv = stats?.overdue_invoices;
				if (overdueCount == null || overdueCount < 1) return null;
				return (
					<div className="border border-red-800/50 bg-red-950/20 rounded-lg p-4">
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-3">
								<div className="p-2 rounded-lg bg-red-900/30">
									<FileText className="h-5 w-5 text-red-400" />
								</div>
								<div>
									<p className="font-semibold text-red-400">
										{overdueCount} Overdue Invoice
										{overdueCount !== 1 ? "s" : ""}
									</p>
									<p className="text-sm text-red-300/70">
										Total: ${stats!.overdue_invoices_total?.toFixed(2)}
									</p>
								</div>
							</div>
							<Button
								variant="outline"
								size="sm"
								className="border-red-800 text-red-400 hover:bg-red-900/30"
								onClick={() => onNavigate("invoices")}
							>
								View Invoices
							</Button>
						</div>
						{/* Show top 3 overdue invoices */}
						{overdueInv && overdueInv.length > 0 && (
							<div className="mt-3 space-y-1.5">
								{overdueInv.slice(0, 3).map((inv: Invoice) => {
									const dueDate = inv.due_date
										? new Date(inv.due_date).toLocaleDateString()
										: "—";
									return (
										<div
											key={inv.id}
											className="flex items-center justify-between text-xs text-red-300/80 px-2 py-1 rounded hover:bg-red-900/20 cursor-pointer"
											onClick={() => onNavigate("invoices")}
										>
											<span>
												{inv.invoice_number
													? `#${inv.invoice_number}`
													: inv.id.slice(-6)}
											</span>
											<span>Due {dueDate}</span>
											<div className="flex items-center gap-2">
												<span className="font-medium">
													${Number(inv.total).toFixed(2)}
												</span>
												<button
													onClick={(e) => {
														e.stopPropagation();
														markPaid.mutate(inv);
													}}
													className="text-[10px] px-1.5 py-0.5 rounded bg-green-600/20 text-green-400 hover:bg-green-600/30"
													title="Mark as paid"
												>
													Pay
												</button>
											</div>
										</div>
									);
								})}
							</div>
						)}
					</div>
				);
			})()}

			{/* My Tickets section */}
			<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
				{/* Service vs Parts Breakdown */}
				<Card>
					<CardHeader className="pb-3">
						<CardTitle className="text-base flex items-center gap-2">
							<Package className="w-4 h-4" /> Service vs Parts
						</CardTitle>
					</CardHeader>
					<CardContent className="h-64">
						{stats?.invoice_item_type_breakdown &&
						stats.invoice_item_type_breakdown.length > 0 ? (
							<>
								<ResponsiveContainer width="100%" height="80%">
									<PieChart>
										<Pie
											data={stats.invoice_item_type_breakdown}
											dataKey="total"
											nameKey="item_type"
											cx="50%"
											cy="50%"
											outerRadius={70}
											label={(props: any) =>
												`${props?.item_type || props?.payload?.item_type || ""}: $${Number(props?.total || props?.payload?.total || 0).toFixed(0)}`
											}
										>
											{stats.invoice_item_type_breakdown.map((_entry, idx) => (
												<Cell
													key={`cell-${idx}`}
													fill={
														idx === 0
															? "var(--color-primary)"
															: "var(--color-muted-foreground)"
													}
												/>
											))}
										</Pie>
										<Tooltip
											contentStyle={{
												background: "var(--color-card)",
												border: "1px solid var(--color-border)",
												borderRadius: "8px",
											}}
											formatter={(_v: any, _n: any, props: any) => [
												`$${Number(props?.payload?.total || 0).toFixed(2)} (${props?.payload?.count || 0} items)`,
												props?.payload?.item_type || "",
											]}
										/>
									</PieChart>
								</ResponsiveContainer>
								<div className="flex justify-center gap-4 text-xs text-muted-foreground">
									{stats.invoice_item_type_breakdown.map((entry) => (
										<span key={entry.item_type}>
											{entry.item_type}: ${entry.total.toFixed(0)} (
											{entry.count})
										</span>
									))}
								</div>
							</>
						) : (
							<div className="flex items-center justify-center h-full text-muted-foreground text-sm">
								No invoice data yet
							</div>
						)}
					</CardContent>
				</Card>
				{/* My assigned tickets */}
				<Card>
					<CardHeader className="pb-3">
						<div className="flex items-center justify-between">
							<CardTitle className="text-base flex items-center gap-2">
								<Ticket className="w-4 h-4" /> My Tickets
							</CardTitle>
							{stats?.my_ticket_counts && (
								<div className="flex gap-2 text-xs">
									{stats.my_ticket_counts.urgent > 0 && (
										<Badge variant="destructive" className="text-xs">
											{stats.my_ticket_counts.urgent} urgent
										</Badge>
									)}
									{stats.my_ticket_counts.high > 0 && (
										<Badge className="text-xs bg-orange-500">
											{stats.my_ticket_counts.high} high
										</Badge>
									)}
									<span className="text-muted-foreground">
										{stats.my_ticket_counts.all} total
									</span>
								</div>
							)}
						</div>
					</CardHeader>
					<CardContent>
						{stats?.my_tickets && stats.my_tickets.length > 0 ? (
							<div className="space-y-2">
								{stats.my_tickets.map((ticket) => {
									const hoursAge =
										(Date.now() - new Date(ticket.created_at).getTime()) /
										3600000;
									const slaColor =
										hoursAge < 4
											? "text-green-400"
											: hoursAge < 24
												? "text-amber-400"
												: hoursAge < 72
													? "text-red-400"
													: "text-red-600";
									return (
										<div
											key={ticket.id}
											className="flex items-center justify-between border rounded-lg p-3 hover:bg-accent"
										>
											<div
												className="flex-1 min-w-0 cursor-pointer"
												onClick={() => onNavigate("tickets")}
											>
												<p className="text-sm font-medium truncate">
													{ticket.title || "Untitled"}
												</p>
												<p className="text-xs text-muted-foreground">
													<span className={`${slaColor}`}>●</span>{" "}
													{ticket.status === "open" ? "Open" : ticket.status}
													{ticket.priority && ` · ${ticket.priority}`}
												</p>
											</div>
											<div className="flex items-center gap-1 ml-2 shrink-0">
												{ticket.status === "open" && (
													<button
														onClick={(e) => {
															e.stopPropagation();
															claimTicket.mutate(ticket.id);
														}}
														className="text-xs px-2 py-1 rounded bg-primary/10 text-primary hover:bg-primary/20"
														title="Assign to me"
													>
														<CheckCircle className="h-3 w-3" />
													</button>
												)}
												<p className="text-sm font-semibold">
													#{ticket.ticket_number || ticket.id.slice(-6)}
												</p>
											</div>
										</div>
									);
								})}
							</div>
						) : (
							<p className="text-sm text-muted-foreground text-center py-6">
								No tickets assigned to you
							</p>
						)}
						{stats?.my_tickets && stats.my_tickets.length > 0 && (
							<Button
								variant="ghost"
								size="sm"
								className="w-full mt-2 text-xs"
								onClick={() => onNavigate("tickets")}
							>
								View all tickets →
							</Button>
						)}
					</CardContent>
				</Card>

				{/* Today's Appointments + Summary */}
				<Card>
					<CardHeader className="pb-3">
						<CardTitle className="text-base flex items-center gap-2">
							<Calendar className="w-4 h-4" /> Today's Appointments
						</CardTitle>
					</CardHeader>
					<CardContent>
						{stats?.today_appointments &&
						stats.today_appointments.length > 0 ? (
							<div className="space-y-2">
								{stats.today_appointments.slice(0, 5).map((appt) => {
									const time = new Date(appt.start_time).toLocaleTimeString(
										[],
										{
											hour: "2-digit",
											minute: "2-digit",
										},
									);
									return (
										<div
											key={appt.id}
											className="flex items-center justify-between border rounded-lg p-2 hover:bg-accent"
										>
											<div
												className="flex-1 min-w-0 cursor-pointer"
												onClick={() => onNavigate("appointments")}
											>
												<p className="text-sm font-medium truncate">
													{appt.title || "Appointment"}
												</p>
												<p className="text-xs text-muted-foreground">
													{time} · {appt.status}
												</p>
											</div>
											<div className="flex items-center gap-1 ml-2 shrink-0">
												{appt.status === "scheduled" && (
													<button
														onClick={(e) => {
															e.stopPropagation();
															updateApptStatus.mutate({
																id: appt.id,
																status: "checked_in",
															});
														}}
														className="text-xs px-2 py-1 rounded bg-green-500/10 text-green-400 hover:bg-green-500/20"
														title="Check in"
													>
														Check In
													</button>
												)}
												{appt.status === "checked_in" && (
													<button
														onClick={(e) => {
															e.stopPropagation();
															updateApptStatus.mutate({
																id: appt.id,
																status: "in_progress",
															});
														}}
														className="text-xs px-2 py-1 rounded bg-blue-500/10 text-blue-400 hover:bg-blue-500/20"
														title="Start service"
													>
														Start
													</button>
												)}
												{(appt.status === "scheduled" ||
													appt.status === "checked_in" ||
													appt.status === "in_progress") && (
													<button
														onClick={(e) => {
															e.stopPropagation();
															updateApptStatus.mutate({
																id: appt.id,
																status: "completed",
															});
														}}
														className="text-xs px-2 py-1 rounded bg-primary/10 text-primary hover:bg-primary/20"
														title="Mark completed"
													>
														✓
													</button>
												)}
											</div>
										</div>
									);
								})}
								<Button
									variant="ghost"
									size="sm"
									className="w-full mt-1 text-xs"
									onClick={() => onNavigate("appointments")}
								>
									View all →
								</Button>
							</div>
						) : (
							<p className="text-sm text-muted-foreground text-center py-6">
								No appointments today
							</p>
						)}
					</CardContent>
				</Card>
			</div>
		</>
	);
}
