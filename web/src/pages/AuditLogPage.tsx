import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api, AuditLogEntry } from "../lib/api";
import { History, Filter, RefreshCw } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

const ENTITY_OPTIONS = [
	"",
	"customer",
	"ticket",
	"invoice",
	"payment",
	"appointment",
	"product",
	"estimate",
	"purchase_order",
	"user",
	"tax_rate",
	"line_item",
	"adjustment",
];
const ACTION_OPTIONS = [
	"",
	"create",
	"update",
	"delete",
	"assign",
	"update_status",
	"convert",
	"receive",
];

function formatTime(ms: number) {
	const d = new Date(ms);
	return d.toLocaleDateString() + " " + d.toLocaleTimeString();
}

function actionBadge(action: string) {
	const colors: Record<string, string> = {
		create: "bg-green-900/40 text-green-300 border-green-700",
		update: "bg-blue-900/40 text-primary/80 border-blue-700",
		update_status: "bg-blue-900/40 text-primary/80 border-blue-700",
		assign: "bg-purple-900/40 text-purple-300 border-purple-700",
		delete: "bg-red-900/40 text-red-300 border-red-700",
		convert: "bg-amber-900/40 text-amber-300 border-amber-700",
		receive: "bg-cyan-900/40 text-cyan-300 border-cyan-700",
	};
	const cls = colors[action] || "bg-muted text-foreground/80 border-border";
	return (
		<span
			className={`inline-block px-2 py-0.5 rounded text-xs font-mono border ${cls}`}
		>
			{action}
		</span>
	);
}

export default function AuditLogPage() {
	const [entityFilter, setEntityFilter] = useState("");
	const [actionFilter, setActionFilter] = useState("");

	const { data, isLoading, error, refetch } = useQuery({
		queryKey: [
			"audit-log",
			{ entity: entityFilter || undefined, action: actionFilter || undefined },
		],
		queryFn: () =>
			api.auditLog.list(
				200,
				entityFilter || undefined,
				actionFilter || undefined,
			),
	});

	useEffect(() => {
		if (error) toast.error("Failed to load audit log");
	}, [error]);

	const entries = data?.entries ?? [];

	return (
		<div className="space-y-6">
			<div className="flex items-start justify-between gap-2 flex-wrap">
				<h1 className="text-2xl font-bold flex items-center gap-2">
					<History className="w-6 h-6 text-primary" />
					Audit Log
				</h1>
				<Button
					onClick={() => refetch()}
					variant="secondary"
					className="flex items-center gap-2"
				>
					<RefreshCw className="w-4 h-4" />
					Refresh
				</Button>
			</div>

			{/* Filters */}
			<Card className="p-4">
				<div className="flex items-center gap-3 flex-wrap">
					<Filter className="w-4 h-4 text-muted-foreground" />
					<select
						value={entityFilter}
						onChange={(e) => setEntityFilter(e.target.value)}
						className="bg-muted border border-border rounded px-3 py-1.5 text-sm text-foreground focus:outline-none focus:border-primary"
					>
						<option value="">All entities</option>
						{ENTITY_OPTIONS.filter(Boolean).map((e) => (
							<option key={e} value={e}>
								{e.replace("_", " ")}
							</option>
						))}
					</select>
					<select
						value={actionFilter}
						onChange={(e) => setActionFilter(e.target.value)}
						className="bg-muted border border-border rounded px-3 py-1.5 text-sm text-foreground focus:outline-none focus:border-primary"
					>
						<option value="">All actions</option>
						{ACTION_OPTIONS.filter(Boolean).map((a) => (
							<option key={a} value={a}>
								{a}
							</option>
						))}
					</select>
				</div>
			</Card>

			{/* Log table */}
			<Card className="overflow-hidden">
				{isLoading ? (
					<div className="p-8 text-center text-muted-foreground">
						Loading...
					</div>
				) : entries.length === 0 ? (
					<div className="p-8 text-center text-muted-foreground">
						No audit log entries yet.
					</div>
				) : (
					<div className="overflow-x-auto">
						<table className="w-full text-sm">
							<thead>
								<tr className="border-b border-border bg-muted/50">
									<th className="text-left px-4 py-3 font-medium text-muted-foreground">
										Time
									</th>
									<th className="text-left px-4 py-3 font-medium text-muted-foreground">
										User
									</th>
									<th className="text-left px-4 py-3 font-medium text-muted-foreground">
										Action
									</th>
									<th className="text-left px-4 py-3 font-medium text-muted-foreground">
										Entity
									</th>
									<th className="text-left px-4 py-3 font-medium text-muted-foreground">
										ID / Detail
									</th>
								</tr>
							</thead>
							<tbody>
								{entries.map((e: AuditLogEntry) => (
									<tr
										key={e.id}
										className="border-b border-border hover:bg-muted/30"
									>
										<td className="px-4 py-3 text-muted-foreground whitespace-nowrap font-mono text-xs">
											{formatTime(e.created_at)}
										</td>
										<td className="px-4 py-3 whitespace-nowrap">
											<span className="font-medium">{e.user_name}</span>
											<span className="text-muted-foreground text-xs ml-2 font-mono">
												{e.user_id?.slice(0, 12)}…
											</span>
										</td>
										<td className="px-4 py-3">{actionBadge(e.action)}</td>
										<td className="px-4 py-3">
											<span className="text-foreground/80">{e.entity}</span>
										</td>
										<td className="px-4 py-3 text-muted-foreground max-w-xs truncate font-mono text-xs">
											{e.entity_id}
											{e.details && (
												<span className="text-muted-foreground ml-2">
													| {e.details}
												</span>
											)}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				)}
			</Card>
		</div>
	);
}
