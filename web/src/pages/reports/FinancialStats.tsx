import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../components/ui/card";
import {
	BarChart,
	Bar,
	XAxis,
	YAxis,
	CartesianGrid,
	Tooltip,
	ResponsiveContainer,
	Cell,
	LineChart,
	Line,
} from "recharts";
import {
	DollarSign,
	Clock,
	Ticket,
	Award,
	FileText,
	Users,
} from "lucide-react";

const INV_STATUS_COLORS: Record<string, string> = {
	draft: "#6b7280",
	sent: "#3b82f6",
	paid: "#22c55e",
	partial: "#f59e0b",
	overdue: "#ef4444",
	cancelled: "#9ca3af",
};

const getInvStatusColor = (status: string) =>
	INV_STATUS_COLORS[status.toLowerCase()] || "#6b7280";

interface Totals {
	total_revenue: number;
	outstanding_revenue: number;
	open_tickets: number;
	avg_resolution_hours?: number;
	sla_breach_rate: number;
	sla_breach_count: number;
	overdue_invoice_rate: number;
	overdue_invoice_count: number;
	total_sent: number;
}

interface FinancialStatsProps {
	revenue_by_month: { month: string; revenue: number }[];
	invoice_by_status: { status: string; count: number }[];
	customers_by_month: { month: string; new_customers: number }[];
	totals: Totals;
}

export default function FinancialStats({
	revenue_by_month,
	invoice_by_status,
	customers_by_month,
	totals,
}: FinancialStatsProps) {
	return (
		<>
			{/* Summary cards */}
			<div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
				{[
					{
						label: "Total Revenue",
						value: `$${totals.total_revenue.toFixed(2)}`,
						icon: DollarSign,
						color: "text-green-400",
					},
					{
						label: "Outstanding",
						value: `$${totals.outstanding_revenue.toFixed(2)}`,
						icon: Clock,
						color: "text-amber-400",
					},
					{
						label: "Open Tickets",
						value: totals.open_tickets,
						icon: Ticket,
						color: "text-blue-400",
					},
					{
						label: "Avg Resolution",
						value: totals.avg_resolution_hours
							? `${totals.avg_resolution_hours}h`
							: "N/A",
						icon: Award,
						color: "text-purple-400",
					},
				].map((card) => {
					const Icon = card.icon;
					return (
						<Card key={card.label}>
							<CardContent className="pt-4">
								<div className="flex items-center gap-3">
									<Icon className={`h-5 w-5 ${card.color}`} />
									<div>
										<p className="text-xs text-muted-foreground">
											{card.label}
										</p>
										<p className="text-lg font-bold">{card.value}</p>
									</div>
								</div>
							</CardContent>
						</Card>
					);
				})}
			</div>

			{/* SLA & Overdue health cards */}
			<div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<Card>
					<CardContent className="pt-4 flex items-center gap-3">
						<div
							className={`h-10 w-10 rounded-full flex items-center justify-center ${
								totals.sla_breach_rate > 50
									? "bg-red-500/20"
									: totals.sla_breach_rate > 20
										? "bg-amber-500/20"
										: "bg-green-500/20"
							}`}
						>
							<Award
								className={`h-5 w-5 ${
									totals.sla_breach_rate > 50
										? "text-red-400"
										: totals.sla_breach_rate > 20
											? "text-amber-400"
											: "text-green-400"
								}`}
							/>
						</div>
						<div>
							<p className="text-xs text-muted-foreground">SLA Breach Rate</p>
							<p className="text-lg font-bold">{totals.sla_breach_rate}%</p>
							<p className="text-xs text-muted-foreground">
								{totals.sla_breach_count} breached of {totals.open_tickets} open
								tickets
							</p>
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="pt-4 flex items-center gap-3">
						<div
							className={`h-10 w-10 rounded-full flex items-center justify-center ${
								totals.overdue_invoice_rate > 50
									? "bg-red-500/20"
									: totals.overdue_invoice_rate > 20
										? "bg-amber-500/20"
										: "bg-green-500/20"
							}`}
						>
							<Clock
								className={`h-5 w-5 ${
									totals.overdue_invoice_rate > 50
										? "text-red-400"
										: totals.overdue_invoice_rate > 20
											? "text-amber-400"
											: "text-green-400"
								}`}
							/>
						</div>
						<div>
							<p className="text-xs text-muted-foreground">
								Overdue Invoice Rate
							</p>
							<p className="text-lg font-bold">
								{totals.overdue_invoice_rate}%
							</p>
							<p className="text-xs text-muted-foreground">
								{totals.overdue_invoice_count} overdue of {totals.total_sent}{" "}
								sent invoices
							</p>
						</div>
					</CardContent>
				</Card>
			</div>

			{/* Revenue by month */}
			<Card>
				<CardHeader>
					<CardTitle className="text-sm flex items-center gap-2">
						<DollarSign className="h-4 w-4 text-green-400" /> Revenue Trend
					</CardTitle>
				</CardHeader>
				<CardContent>
					<ResponsiveContainer width="100%" height={250}>
						<BarChart data={revenue_by_month}>
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
							/>
							<Tooltip
								contentStyle={{
									background: "var(--color-card)",
									border: "1px solid var(--color-border)",
									borderRadius: "8px",
								}}
								formatter={(value: any) => [
									`$${Number(value || 0).toFixed(2)}`,
									"Revenue",
								]}
							/>
							<Bar dataKey="revenue" fill="#22c55e" radius={[4, 4, 0, 0]} />
						</BarChart>
					</ResponsiveContainer>
				</CardContent>
			</Card>

			{/* Invoice by status */}
			<Card>
				<CardHeader>
					<CardTitle className="text-sm flex items-center gap-2">
						<FileText className="h-4 w-4 text-purple-400" /> Invoices by Status
					</CardTitle>
				</CardHeader>
				<CardContent>
					<ResponsiveContainer width="100%" height={250}>
						<BarChart data={invoice_by_status} layout="vertical">
							<CartesianGrid
								strokeDasharray="3 3"
								stroke="var(--color-border)"
							/>
							<XAxis
								type="number"
								tick={{ fontSize: 11 }}
								stroke="var(--color-muted-foreground)"
							/>
							<YAxis
								type="category"
								dataKey="status"
								tick={{ fontSize: 11 }}
								stroke="var(--color-muted-foreground)"
							/>
							<Tooltip
								contentStyle={{
									background: "var(--color-card)",
									border: "1px solid var(--color-border)",
									borderRadius: "8px",
								}}
							/>
							<Bar dataKey="count" radius={[0, 4, 4, 0]}>
								{invoice_by_status.map((entry) => (
									<Cell
										key={entry.status}
										fill={getInvStatusColor(entry.status)}
									/>
								))}
							</Bar>
						</BarChart>
					</ResponsiveContainer>
				</CardContent>
			</Card>

			{/* Customer Acquisition by Month */}
			<Card>
				<CardHeader>
					<CardTitle className="text-sm flex items-center gap-2">
						<Users className="h-4 w-4 text-blue-400" /> Customer Acquisition
					</CardTitle>
				</CardHeader>
				<CardContent>
					<ResponsiveContainer width="100%" height={250}>
						<BarChart data={customers_by_month}>
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
								allowDecimals={false}
							/>
							<Tooltip
								contentStyle={{
									background: "var(--color-card)",
									border: "1px solid var(--color-border)",
									borderRadius: "8px",
								}}
								formatter={(value: any) => [value, "New Customers"]}
							/>
							<Bar
								dataKey="new_customers"
								fill="#3b82f6"
								radius={[4, 4, 0, 0]}
							/>
						</BarChart>
					</ResponsiveContainer>
				</CardContent>
			</Card>
		</>
	);
}
