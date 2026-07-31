import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../../lib/query-client";
import { api, BusinessHours, DayHours } from "../../lib/api";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Clock, Loader2, CheckCircle, XCircle } from "lucide-react";
import { toast } from "sonner";

const DAY_KEYS = [
	"monday",
	"tuesday",
	"wednesday",
	"thursday",
	"friday",
	"saturday",
	"sunday",
] as const;
const DAY_LABELS: Record<string, string> = {
	monday: "Monday",
	tuesday: "Tuesday",
	wednesday: "Wednesday",
	thursday: "Thursday",
	friday: "Friday",
	saturday: "Saturday",
	sunday: "Sunday",
};

const defaultHours: BusinessHours = {
	monday: { enabled: true, open: "09:00", close: "18:00" },
	tuesday: { enabled: true, open: "09:00", close: "18:00" },
	wednesday: { enabled: true, open: "09:00", close: "18:00" },
	thursday: { enabled: true, open: "09:00", close: "18:00" },
	friday: { enabled: true, open: "09:00", close: "18:00" },
	saturday: { enabled: false, open: "10:00", close: "14:00" },
	sunday: { enabled: false, open: "10:00", close: "14:00" },
};

export default function BusinessHoursSection() {
	const [hours, setHours] = useState<BusinessHours>(defaultHours);

	const { data: hoursData } = useQuery({
		queryKey: ["business-hours"],
		queryFn: () => api.settings.businessHours.get(),
	});

	useEffect(() => {
		if (hoursData?.hours) {
			setHours({ ...defaultHours, ...hoursData.hours });
		}
	}, [hoursData]);

	const saveMutation = useMutation({
		mutationFn: (data: BusinessHours) => api.settings.businessHours.save(data),
		onSuccess: () => {
			toast.success("Business hours saved");
			queryClient.invalidateQueries({ queryKey: ["business-hours"] });
		},
		onError: () => toast.error("Failed to save business hours"),
	});

	const updateDay = (day: string, field: string, value: boolean | string) => {
		setHours((prev) => ({
			...prev,
			[day]: { ...prev[day as keyof BusinessHours], [field]: value },
		}));
	};

	return (
		<Card>
			<CardHeader>
				<CardTitle className="flex items-center gap-2">
					<Clock className="h-4 w-4" />
					Business Hours
					{hoursData?.configured && (
						<Badge variant="success" className="ml-2 text-xs">
							Configured
						</Badge>
					)}
				</CardTitle>
			</CardHeader>
			<CardContent className="space-y-4">
				<p className="text-sm text-muted-foreground">
					Set your shop's operating hours. These determine when appointments can
					be scheduled and which time slots are available in the calendar.
				</p>

				<div className="space-y-2">
					{DAY_KEYS.map((day) => (
						<div
							key={day}
							className="flex items-center gap-3 p-2 rounded bg-muted/30"
						>
							<label className="flex items-center gap-2 w-28">
								<input
									type="checkbox"
									checked={hours[day].enabled}
									onChange={(e) => updateDay(day, "enabled", e.target.checked)}
									className="rounded border-border accent-primary"
								/>
								<span
									className={`text-sm font-medium ${hours[day].enabled ? "" : "text-muted-foreground line-through"}`}
								>
									{DAY_LABELS[day]}
								</span>
							</label>
							{hours[day].enabled ? (
								<>
									<Input
										type="time"
										value={hours[day].open}
										onChange={(e) => updateDay(day, "open", e.target.value)}
										className="w-28"
									/>
									<span className="text-xs text-muted-foreground">to</span>
									<Input
										type="time"
										value={hours[day].close}
										onChange={(e) => updateDay(day, "close", e.target.value)}
										className="w-28"
									/>
								</>
							) : (
								<span className="text-xs text-muted-foreground italic">
									Closed
								</span>
							)}
						</div>
					))}
				</div>

				<div className="flex gap-2">
					<Button
						onClick={() => saveMutation.mutate(hours)}
						disabled={saveMutation.isPending}
					>
						{saveMutation.isPending ? (
							<>
								<Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
								Saving...
							</>
						) : (
							"Save Hours"
						)}
					</Button>
					<Button variant="outline" onClick={() => setHours(defaultHours)}>
						Reset to Defaults
					</Button>
				</div>

				<div className="border-t pt-3">
					<p className="text-xs text-muted-foreground">
						<strong>How this is used:</strong> The appointment scheduler will
						only offer time slots within operating hours. Days marked as closed
						won't appear in the date picker. Future features will add lunch
						breaks and holiday closures.
					</p>
				</div>
			</CardContent>
		</Card>
	);
}
