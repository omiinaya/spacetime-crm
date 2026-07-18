import { useState } from "react";
import type { AuditLogEntry } from "../lib/api-types";

import { useQuery } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api } from "../lib/api";
import { History, Filter, RefreshCw } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";

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
		update: "bg-blue-900/40 text-blue-300 border-blue-700",
		update_status: "bg-blue-900/40 text-blue-300 border-blue-700",
		assign: "bg-purple-900/40 text-purple-300 border-purple-700",
		delete: "bg-red-900/40 text-red-300 border-red-700",
		convert: "bg-amber-900/40 text-amber-300 border-amber-700",
		receive: "bg-cyan-900/40 text-cyan-300 border-cyan-700",
	};
	const cls = colors[action] || "bg-slate-700 text-slate-300 border-slate-600";
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

	const entries = data?.entries ?? [];

	return (
		<div className="space-y-6">
			<div className="flex items-start justify-between gap-2 flex-wrap">
				<h1 className="text-2xl font-bold flex items-center gap-2">
					<History className="w-6 h-6 text-blue-400" />
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
					<Filter className="w-4 h-4 text-slate-400" />
					<select
						value={entityFilter}
						onChange={(e) => setEntityFilter(e.target.value)}
						className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
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
						className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
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

			{/* Error state */}
			{error ? (
				<Card className="overflow-hidden">
					<div className="p-8 text-center">
						<div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mx-auto mb-4">
							<svg className="h-6 w-6 text-destructive" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
								<path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
							</svg>
						</div>
						<h3 className="text-lg font-semibold mb-1">Failed to load audit log</h3>
						<p className="text-sm text-muted-foreground">{error?.message || "An unexpected error occurred"}</p>
						<button
							onClick={() => refetch()}
							className="mt-4 text-sm px-4 py-2 bg-primary/10 text-primary rounded-md hover:bg-primary/20"
						>
							Retry
						</button>
					</div>
				</Card>
			) : (
				<Card className="overflow-hidden">
				{isLoading ? (
					<div className="p-8 text-center text-slate-400">Loading...</div>
				) : entries.length === 0 ? (
					<div className="p-8 text-center text-slate-400">
						No audit log entries yet.
					</div>
				) : (
					<div className="overflow-x-auto">
						<table className="w-full text-sm">
							<thead>
								<tr className="border-b border-slate-700 bg-slate-800/50">
									<th className="text-left px-4 py-3 font-medium text-slate-400">
										Time
									</th>
									<th className="text-left px-4 py-3 font-medium text-slate-400">
										User
									</th>
									<th className="text-left px-4 py-3 font-medium text-slate-400">
										Action
									</th>
									<th className="text-left px-4 py-3 font-medium text-slate-400">
										Entity
									</th>
									<th className="text-left px-4 py-3 font-medium text-slate-400">
										ID / Detail
									</th>
								</tr>
							</thead>
							<tbody>
								{entries.map((e: AuditLogEntry) => (
									<tr
										key={e.id}
										className="border-b border-slate-800 hover:bg-slate-800/30"
									>
										<td className="px-4 py-3 text-slate-400 whitespace-nowrap font-mono text-xs">
											{formatTime(e.created_at)}
										</td>
										<td className="px-4 py-3 whitespace-nowrap">
											<span className="font-medium">{e.user_name}</span>
											<span className="text-slate-500 text-xs ml-2 font-mono">
												{e.user_id?.slice(0, 12)}…
											</span>
										</td>
										<td className="px-4 py-3">{actionBadge(e.action)}</td>
										<td className="px-4 py-3">
											<span className="text-slate-300">{e.entity}</span>
										</td>
										<td className="px-4 py-3 text-slate-400 max-w-xs truncate font-mono text-xs">
											{e.entity_id}
											{e.details && (
												<span className="text-slate-500 ml-2">
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
			)}
		</div>
	);
}
