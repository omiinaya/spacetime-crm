import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../../lib/api";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../components/ui/card";
import { Select } from "../../components/ui/select";
import { Button } from "../../components/ui/button";
import { toast } from "sonner";
import { Clock, Save } from "lucide-react";
import { queryClient } from "../../lib/query-client";

const INTERVAL_OPTIONS = [1, 3, 7, 14];
const DEFAULT_INTERVAL = 3;

export default function ReminderScheduleSection() {
	const { data, isLoading } = useQuery({
		queryKey: ["settings", "app"],
		queryFn: () => api.settings.app.get(),
	});

	const [intervalDays, setIntervalDays] = useState(DEFAULT_INTERVAL);
	const [touched, setTouched] = useState(false);

	useEffect(() => {
		// Hydrate from the server only until the user makes a change —
		// otherwise a late-arriving fetch response would clobber their selection.
		if (data?.config?.reminder_interval_days && !touched) {
			setIntervalDays(data.config.reminder_interval_days);
		}
	}, [data, touched]);

	const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
		setIntervalDays(Number(e.target.value));
		setTouched(true);
	};

	const mutation = useMutation({
		mutationFn: () =>
			api.settings.app.save({ reminder_interval_days: intervalDays }),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["settings", "app"] });
			toast.success("Reminder schedule updated");
		},
		onError: () => toast.error("Failed to save reminder schedule"),
	});

	return (
		<Card>
			<CardHeader>
				<CardTitle className="flex items-center gap-2">
					<Clock className="h-4 w-4 text-muted-foreground" />
					Overdue Reminder Schedule
				</CardTitle>
			</CardHeader>
			<CardContent className="space-y-4">
				<p className="text-sm text-muted-foreground">
					Send overdue invoice reminders only after an invoice has been past due
					for this many days.
				</p>
				<div className="flex items-center gap-2 max-w-xs">
					<Select
						value={String(intervalDays)}
						onChange={handleChange}
						aria-label="Reminder interval in days"
						disabled={isLoading}
					>
						{INTERVAL_OPTIONS.map((days) => (
							<option key={days} value={days}>
								{days} day{days === 1 ? "" : "s"}
							</option>
						))}
					</Select>
					<Button
						onClick={() => mutation.mutate()}
						disabled={mutation.isPending || isLoading}
					>
						<Save className="h-4 w-4 mr-1" />
						Save
					</Button>
				</div>
			</CardContent>
		</Card>
	);
}
