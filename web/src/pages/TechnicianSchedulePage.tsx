import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, Appointment } from "../lib/api";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
	Calendar,
	CalendarClock,
	ChevronLeft,
	ChevronRight,
	Clock,
	User,
} from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
	scheduled: "bg-blue-500/20 text-blue-400 border-blue-500/30",
	confirmed: "bg-green-500/20 text-green-400 border-green-500/30",
	"in progress": "bg-amber-500/20 text-amber-400 border-amber-500/30",
	completed: "bg-slate-500/20 text-muted-foreground border-slate-500/30",
	cancelled: "bg-red-500/20 text-red-400 border-red-500/30",
	"no-show": "bg-red-500/20 text-red-400 border-red-500/30",
};

function getStatusBadge(status: string) {
	const cls =
		STATUS_COLORS[status.toLowerCase()] ||
		"bg-slate-500/20 text-muted-foreground border-slate-500/30";
	return (
		<span
			className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${cls}`}
		>
			{status}
		</span>
	);
}

function fmtTime(ts: number) {
	return new Date(ts).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
}

function fmtDate(ts: number) {
	return new Date(ts).toLocaleDateString([], {
		weekday: "short",
		month: "short",
		day: "numeric",
	});
}

export default function TechnicianSchedulePage() {
	const [selectedTech, setSelectedTech] = useState("");
	const [currentMonth, setCurrentMonth] = useState(() => {
		const now = new Date();
		return new Date(now.getFullYear(), now.getMonth(), 1);
	});

	const monthStart = currentMonth.getTime();
	const monthEnd = new Date(
		currentMonth.getFullYear(),
		currentMonth.getMonth() + 1,
		0,
		23,
		59,
		59,
	).getTime();

	// Fetch all staff users for the tech selector
	const { data: usersData } = useQuery({
		queryKey: ["users"],
		queryFn: async () => {
			const res = await api.users.list();
			return res.users.filter(
				(u: { role: string; active: boolean }) =>
					(u.role === "admin" || u.role === "tech") && u.active !== false,
			);
		},
		staleTime: 60000,
	});

	// Fetch appointments grouped by tech
	const { data, isLoading } = useQuery({
		queryKey: ["appointments-by-tech", monthStart, monthEnd],
		queryFn: () => api.appointments.byTech(monthStart, monthEnd),
		staleTime: 30000,
	});

	const groups = data?.groups ?? [];
	const unassigned = data?.unassigned ?? [];

	// Get the selected tech's appointments
	const selectedGroup = selectedTech
		? groups.find((g) => g.user_id === selectedTech)
		: null;
	const selectedAppts = selectedGroup?.appointments ?? [];

	// Group appointments by day
	const byDay: Record<string, Appointment[]> = {};
	for (const appt of selectedAppts) {
		const dayKey = fmtDate(appt.start_time);
		if (!byDay[dayKey]) byDay[dayKey] = [];
		byDay[dayKey].push(appt);
	}

	const prevMonth = () =>
		setCurrentMonth(
			new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1),
		);
	const nextMonth = () =>
		setCurrentMonth(
			new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1),
		);

	// Show "This Month" button if not on current month
	const isCurrentMonth =
		currentMonth.getMonth() === new Date().getMonth() &&
		currentMonth.getFullYear() === new Date().getFullYear();

	return (
		<div className="space-y-6">
			<div className="flex items-start justify-between gap-4 flex-wrap">
				<div>
					<h1 className="text-2xl font-bold flex items-center gap-2">
						<CalendarClock className="h-6 w-6 text-purple-400" />
						Technician Schedule
					</h1>
					<p className="text-sm text-muted-foreground mt-1">
						View appointments by technician
					</p>
				</div>
			</div>

			{/* Controls */}
			<Card>
				<CardContent className="pt-4">
					<div className="flex items-center gap-3 flex-wrap">
						<div className="flex items-center gap-1">
							<Button variant="ghost" size="icon" onClick={prevMonth}>
								<ChevronLeft className="h-4 w-4" />
							</Button>
							<span className="text-sm font-medium min-w-[140px] text-center">
								{currentMonth.toLocaleDateString([], {
									month: "long",
									year: "numeric",
								})}
							</span>
							<Button variant="ghost" size="icon" onClick={nextMonth}>
								<ChevronRight className="h-4 w-4" />
							</Button>
							{!isCurrentMonth && (
								<Button
									variant="outline"
									size="sm"
									onClick={() =>
										setCurrentMonth(
											new Date(
												new Date().getFullYear(),
												new Date().getMonth(),
												1,
											),
										)
									}
								>
									This Month
								</Button>
							)}
						</div>

						<div className="flex-1" />

						{/* Tech selector */}
						<div className="flex items-center gap-2">
							<User className="h-4 w-4 text-muted-foreground" />
							<select
								value={selectedTech}
								onChange={(e) => setSelectedTech(e.target.value)}
								className="h-9 rounded-md border border-input bg-background px-3 text-xs outline-none focus:ring-2 focus:ring-ring min-w-[160px]"
							>
								<option value="">All technicians</option>
								{usersData?.map((u: { id: string; name: string }) => (
									<option key={u.id} value={u.id}>
										{u.name}
									</option>
								))}
							</select>
						</div>

						{/* Summary */}
						<div className="text-xs text-muted-foreground">
							{selectedGroup
								? `${selectedGroup.appointments.length} appointment(s)`
								: `${groups.reduce((sum, g) => sum + g.appointments.length, 0)} appointment(s) across ${groups.length} tech(s)`}
							{unassigned.length > 0 && ` + ${unassigned.length} unassigned`}
						</div>
					</div>
				</CardContent>
			</Card>

			{/* Loading state */}
			{isLoading ? (
				<div className="flex items-center justify-center py-16">
					<div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
				</div>
			) : (
				<>
					{/* If no tech selected: show per-tech summary cards */}
					{!selectedTech && (
						<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
							{groups.map((g) => (
								<Card
									key={g.user_id}
									className="cursor-pointer hover:border-primary/50 transition-colors"
									onClick={() => setSelectedTech(g.user_id)}
								>
									<CardContent className="pt-4">
										<div className="flex items-center gap-3 mb-3">
											<div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
												<User className="h-4 w-4 text-primary" />
											</div>
											<div>
												<p className="font-medium text-sm">{g.user_name}</p>
												<p className="text-xs text-muted-foreground">
													{g.appointments.length} appointment(s)
												</p>
											</div>
										</div>
										{/* Show first few appointments */}
										<div className="space-y-1">
											{g.appointments.slice(0, 3).map((a) => (
												<div
													key={a.id}
													className="flex items-center gap-2 text-xs text-muted-foreground"
												>
													<Clock className="h-3 w-3 shrink-0" />
													<span>{fmtTime(a.start_time)}</span>
													<span className="truncate">{a.title}</span>
												</div>
											))}
											{g.appointments.length > 3 && (
												<p className="text-xs text-muted-foreground">
													+{g.appointments.length - 3} more
												</p>
											)}
										</div>
									</CardContent>
								</Card>
							))}
							{groups.length === 0 && !isLoading && (
								<p className="col-span-full text-center text-muted-foreground py-8">
									No appointments scheduled for this month.
								</p>
							)}
						</div>
					)}

					{/* Tech-specific: show appointments grouped by day */}
					{selectedTech && (
						<div className="space-y-4">
							{Object.entries(byDay).length === 0 ? (
								<div className="text-center py-16 text-muted-foreground">
									<Calendar className="h-12 w-12 mx-auto mb-3 opacity-30" />
									<p>
										No appointments for {selectedGroup?.user_name} this month.
									</p>
								</div>
							) : (
								Object.entries(byDay).map(([day, appts]) => (
									<div key={day}>
										<h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
											<Calendar className="h-4 w-4 text-primary" />
											{day}
											<span className="text-xs text-muted-foreground font-normal">
												({appts.length} appointment
												{appts.length !== 1 ? "s" : ""})
											</span>
										</h3>
										<div className="space-y-2 ml-1">
											{appts.map((a) => (
												<Card
													key={a.id}
													className="border-l-4"
													style={{
														borderLeftColor: a.color || "var(--color-border)",
													}}
												>
													<CardContent className="p-3 flex items-center justify-between gap-3">
														<div className="min-w-0 flex-1">
															<div className="flex items-center gap-2">
																<span className="text-xs font-mono text-muted-foreground">
																	{fmtTime(a.start_time)} –{" "}
																	{fmtTime(a.end_time)}
																</span>
																{getStatusBadge(a.status)}
															</div>
															<p className="text-sm font-medium mt-0.5 truncate">
																{a.title}
															</p>
															<p className="text-xs text-muted-foreground truncate">
																{a.description?.slice(0, 80)}
																{a.description?.length > 80 ? "…" : ""}
															</p>
														</div>
														{a.customer_id && (
															<div className="text-xs text-muted-foreground shrink-0 text-right">
																<span>ID: {a.customer_id.slice(0, 12)}…</span>
															</div>
														)}
													</CardContent>
												</Card>
											))}
										</div>
									</div>
								))
							)}

							<Button
								variant="outline"
								size="sm"
								onClick={() => setSelectedTech("")}
							>
								← Back to all techs
							</Button>
						</div>
					)}
				</>
			)}
		</div>
	);
}
