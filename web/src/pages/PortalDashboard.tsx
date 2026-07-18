import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { portalApi, PortalStats, usePortalAuth } from "../lib/portal-auth";
import { Card, CardContent } from "../components/ui/card";
import { Ticket, FileText, Calendar, DollarSign } from "lucide-react";

export default function PortalDashboard() {
	const { customer } = usePortalAuth();
	const [stats, setStats] = useState<PortalStats | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		portalApi.stats
			.get()
			.then((s) => {
				setStats(s);
				setLoading(false);
			})
			.catch((err) => {
				setError(err?.message || "Failed to load dashboard stats");
				setLoading(false);
			});
	}, []);

	const cards = [
		{
			label: "Open Tickets",
			value: stats?.open_tickets ?? "—",
			icon: Ticket,
			color: "text-blue-500",
		},
		{
			label: "Total Invoices",
			value: stats?.total_invoices ?? "—",
			icon: FileText,
			color: "text-orange-500",
		},
		{
			label: "Balance Due",
			value:
				stats?.balance_due != null ? `$${stats.balance_due.toFixed(2)}` : "—",
			icon: DollarSign,
			color: stats?.balance_due ? "text-red-500" : "text-green-500",
		},
		{
			label: "Upcoming Appts",
			value: stats?.upcoming_appointments ?? "—",
			icon: Calendar,
			color: "text-purple-500",
		},
	];

	if (loading) {
		return (
			<div className="flex items-center justify-center py-20">
				<Loader2 className="h-8 w-8 animate-spin text-primary" />
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex flex-col items-center justify-center py-20 text-center">
				<div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
					<svg
						className="h-6 w-6 text-destructive"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
						strokeWidth={2}
					>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
						/>
					</svg>
				</div>
				<h3 className="text-lg font-semibold mb-1">Failed to load dashboard</h3>
				<p className="text-sm text-muted-foreground">{error}</p>
			</div>
		);
	}

	return (
		<div>
			<h1 className="text-2xl font-bold">
				Welcome{customer?.first_name ? `, ${customer.first_name}` : ""}!
			</h1>
			<p className="text-sm text-muted-foreground mt-1">
				Here's your account at a glance
			</p>
			<div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
				{cards.map((c) => {
					const Icon = c.icon;
					return (
						<Card key={c.label}>
							<CardContent className="pt-6">
								<div className="flex items-center gap-3">
									<Icon className={`h-8 w-8 ${c.color}`} />
									<div>
										<p className="text-2xl font-bold">{c.value}</p>
										<p className="text-xs text-muted-foreground">{c.label}</p>
									</div>
								</div>
							</CardContent>
						</Card>
					);
				})}
			</div>
		</div>
	);
}
