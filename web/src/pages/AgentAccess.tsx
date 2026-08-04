import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { RefreshCw, ShieldCheck, ShieldX, Bot } from "lucide-react";
import { api } from "../lib/api";
import type { HermesIdAgent } from "../lib/api/hermes-id-agents";
import { Button } from "../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import { Badge } from "../components/ui/badge";

function formatDate(value: string | undefined | null): string {
	if (!value) return "—";
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return date.toLocaleString();
}

export default function AgentAccessPage() {
	const [agents, setAgents] = useState<HermesIdAgent[]>([]);
	const [total, setTotal] = useState(0);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [refreshing, setRefreshing] = useState(false);
	const [busyDid, setBusyDid] = useState<string | null>(null);

	const load = useCallback(async (silent = false) => {
		if (silent) {
			setRefreshing(true);
		} else {
			setLoading(true);
			setError(null);
		}
		try {
			const data = await api.hermesIdAgents.list("pending");
			setAgents(data.agents || []);
			setTotal(data.total ?? 0);
			setError(null);
		} catch (e: unknown) {
			const message = (e as Error).message || "Failed to load agents";
			setError(message);
			if (!silent) toast.error(message);
		} finally {
			setLoading(false);
			setRefreshing(false);
		}
	}, []);

	useEffect(() => {
		load();
	}, [load]);

	const handleApprove = async (agent: HermesIdAgent) => {
		if (
			!window.confirm(
				`Approve agent "${agent.display_name || agent.did}" for project access?`,
			)
		)
			return;
		setBusyDid(agent.did);
		try {
			await api.hermesIdAgents.approve(agent.did);
			toast.success(`Agent ${agent.display_name || agent.did} approved`);
			await load(true);
		} catch (e: unknown) {
			toast.error((e as Error).message || "Failed to approve agent");
		} finally {
			setBusyDid(null);
		}
	};

	const handleDeny = async (agent: HermesIdAgent) => {
		if (
			!window.confirm(
				`Deny agent "${agent.display_name || agent.did}"? This cannot be undone from this page.`,
			)
		)
			return;
		setBusyDid(agent.did);
		try {
			await api.hermesIdAgents.deny(agent.did);
			toast.success(`Agent ${agent.display_name || agent.did} denied`);
			await load(true);
		} catch (e: unknown) {
			toast.error((e as Error).message || "Failed to deny agent");
		} finally {
			setBusyDid(null);
		}
	};

	return (
		<div className="space-y-6">
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-bold">Agent Access</h1>
					<p className="text-sm text-muted-foreground mt-1">
						Approve or deny hermes-id AI agents requesting access to this
						project
					</p>
				</div>
				<Button
					variant="outline"
					onClick={() => load(true)}
					disabled={refreshing || loading}
				>
					<RefreshCw
						className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`}
					/>
					Refresh
				</Button>
			</div>

			<Card>
				<CardHeader>
					<CardTitle className="flex items-center justify-between">
						<span>Pending Agents</span>
						{!loading && (
							<Badge variant="secondary" className="text-xs">
								{total} pending
							</Badge>
						)}
					</CardTitle>
				</CardHeader>
				<CardContent>
					{loading && (
						<div className="flex items-center justify-center py-16">
							<div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
						</div>
					)}

					{!loading && error && (
						<div className="py-10 text-center space-y-3">
							<p className="text-sm text-destructive">{error}</p>
							<Button variant="outline" size="sm" onClick={() => load()}>
								<RefreshCw className="h-3.5 w-3.5 mr-1" />
								Retry
							</Button>
						</div>
					)}

					{!loading && !error && agents.length === 0 && (
						<div className="py-16 text-center">
							<Bot className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
							<p className="text-sm text-muted-foreground">
								No pending agent requests. New agents requesting access will
								appear here.
							</p>
						</div>
					)}

					{!loading && !error && agents.length > 0 && (
						<div className="overflow-x-auto">
							<table className="w-full text-sm">
								<thead>
									<tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
										<th className="py-2 pr-3 font-medium">Agent DID</th>
										<th className="py-2 pr-3 font-medium">Display Name</th>
										<th className="py-2 pr-3 font-medium">Registered</th>
										<th className="py-2 pr-3 font-medium">
											Requested Projects
										</th>
										<th className="py-2 pr-3 font-medium">Status</th>
										<th className="py-2 font-medium text-right">Actions</th>
									</tr>
								</thead>
								<tbody>
									{agents.map((agent) => (
										<tr
											key={agent.did}
											className="border-b border-border/60 last:border-0 hover:bg-muted/40"
										>
											<td className="py-3 pr-3">
												<span className="font-mono text-xs break-all">
													{agent.did}
												</span>
											</td>
											<td className="py-3 pr-3">
												{agent.display_name || (
													<span className="text-muted-foreground">—</span>
												)}
											</td>
											<td className="py-3 pr-3 text-muted-foreground whitespace-nowrap">
												{formatDate(agent.registered_at)}
											</td>
											<td className="py-3 pr-3">
												<div className="flex flex-wrap gap-1">
													{(agent.projects && agent.projects.length > 0
														? agent.projects
														: ["spacetime-crm"]
													).map((project) => (
														<Badge
															key={project}
															variant="outline"
															className="text-[10px] font-mono"
														>
															{project}
														</Badge>
													))}
												</div>
											</td>
											<td className="py-3 pr-3">
												<Badge variant="warning" className="text-[10px]">
													{agent.status}
												</Badge>
											</td>
											<td className="py-3 text-right whitespace-nowrap">
												<div className="flex justify-end gap-2">
													<Button
														size="sm"
														variant="outline"
														disabled={busyDid === agent.did}
														onClick={() => handleApprove(agent)}
													>
														<ShieldCheck className="h-3.5 w-3.5 mr-1 text-[var(--color-success)]" />
														Approve
													</Button>
													<Button
														size="sm"
														variant="outline"
														disabled={busyDid === agent.did}
														onClick={() => handleDeny(agent)}
													>
														<ShieldX className="h-3.5 w-3.5 mr-1 text-destructive" />
														Deny
													</Button>
												</div>
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					)}
				</CardContent>
			</Card>
		</div>
	);
}
