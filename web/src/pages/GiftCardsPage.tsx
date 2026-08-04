import { useState, useCallback, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type GiftCard } from "../lib/api";
import { Button } from "../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import {
	Gift,
	Search,
	Loader2,
	Plus,
	RotateCcw,
	Check,
	X,
	Copy,
	Ban,
	TicketCheck,
} from "lucide-react";
import { toast } from "sonner";

export default function GiftCardsPage() {
	const queryClient = useQueryClient();
	const [search, setSearch] = useState("");
	const [filter, setFilter] = useState<string>("");
	const [showCreate, setShowCreate] = useState(false);
	const [createAmount, setCreateAmount] = useState("");
	const [createCustomer, setCreateCustomer] = useState("");
	const [createLoading, setCreateLoading] = useState(false);
	const [lookupCode, setLookupCode] = useState("");
	const [lookupResult, setLookupResult] = useState<GiftCard | null>(null);
	const [lookupLoading, setLookupLoading] = useState(false);
	const copyTimer = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

	// ── List gift cards ──
	const { data, isLoading } = useQuery({
		queryKey: ["gift-cards", filter],
		queryFn: () => api.giftCards.list(0, 100, filter),
	});

	// ── Void mutation ──
	const voidMutation = useMutation({
		mutationFn: (id: string) => api.giftCards.void_(id),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["gift-cards"] });
			toast.success("Gift card voided");
		},
		onError: () => toast.error("Failed to void gift card"),
	});

	// ── Copy code to clipboard ──
	const copyCode = useCallback((code: string) => {
		navigator.clipboard.writeText(code).then(() => {
			toast.success("Code copied");
		});
	}, []);

	// ── Lookup gift card ──
	const handleLookup = useCallback(async () => {
		const code = lookupCode.trim().toUpperCase();
		if (!code) {
			toast.error("Enter a gift card code");
			return;
		}
		setLookupLoading(true);
		setLookupResult(null);
		try {
			const res = await api.giftCards.lookup(code);
			setLookupResult(res.gift_card);
		} catch {
			toast.error("Gift card not found");
		} finally {
			setLookupLoading(false);
		}
	}, [lookupCode]);

	// ── Create gift card ──
	const handleCreate = useCallback(async () => {
		const amount = parseFloat(createAmount);
		if (!amount || amount <= 0) {
			toast.error("Enter a valid amount");
			return;
		}
		setCreateLoading(true);
		try {
			const res = await api.giftCards.create({
				amount,
				customer_name: createCustomer || undefined,
			});
			if (res.ok) {
				toast.success(
					`Gift card created: ${res.gift_card.code} — $${amount.toFixed(2)}`,
				);
				setCreateAmount("");
				setCreateCustomer("");
				setShowCreate(false);
				queryClient.invalidateQueries({ queryKey: ["gift-cards"] });
			}
		} catch {
			toast.error("Failed to create gift card");
		} finally {
			setCreateLoading(false);
		}
	}, [createAmount, createCustomer, queryClient]);

	const giftCards = data?.gift_cards ?? [];

	return (
		<div className="p-4 max-w-5xl mx-auto space-y-6">
			<div className="flex items-center justify-between">
				<h1 className="text-xl font-bold flex items-center gap-2">
					<Gift className="w-5 h-5" /> Gift Cards
				</h1>
				<Button onClick={() => setShowCreate(!showCreate)} size="sm">
					{showCreate ? (
						<>
							<X className="w-4 h-4 mr-1" /> Cancel
						</>
					) : (
						<>
							<Plus className="w-4 h-4 mr-1" /> New Gift Card
						</>
					)}
				</Button>
			</div>

			{/* ── Create form ── */}
			{showCreate && (
				<Card>
					<CardHeader className="pb-2">
						<CardTitle className="text-sm">Create Gift Card</CardTitle>
					</CardHeader>
					<CardContent>
						<div className="flex gap-2">
							<div className="flex-1">
								<label className="text-xs text-muted-foreground mb-1 block">
									Amount ($)
								</label>
								<Input
									placeholder="0.00"
									value={createAmount}
									onChange={(e) => setCreateAmount(e.target.value)}
									type="number"
									step="0.01"
									min="1"
								/>
							</div>
							<div className="flex-1">
								<label className="text-xs text-muted-foreground mb-1 block">
									Customer (optional)
								</label>
								<Input
									placeholder="Customer name"
									value={createCustomer}
									onChange={(e) => setCreateCustomer(e.target.value)}
								/>
							</div>
							<div className="flex items-end">
								<Button
									onClick={handleCreate}
									disabled={
										createLoading ||
										!createAmount ||
										parseFloat(createAmount) <= 0
									}
								>
									{createLoading ? (
										<Loader2 className="w-4 h-4 animate-spin mr-1" />
									) : (
										<Gift className="w-4 h-4 mr-1" />
									)}
									Issue
								</Button>
							</div>
						</div>
					</CardContent>
				</Card>
			)}

			{/* ── Quick lookup ── */}
			<Card>
				<CardHeader className="pb-2">
					<CardTitle className="text-sm flex items-center gap-2">
						<TicketCheck className="w-4 h-4" /> Lookup Gift Card
					</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="flex gap-2">
						<Input
							placeholder="Enter gift card code"
							value={lookupCode}
							onChange={(e) => {
								setLookupCode(e.target.value.toUpperCase());
								setLookupResult(null);
							}}
							className="flex-1 uppercase"
							onKeyDown={(e) => {
								if (e.key === "Enter") handleLookup();
							}}
						/>
						<Button
							variant="outline"
							onClick={handleLookup}
							disabled={lookupLoading || !lookupCode.trim()}
						>
							{lookupLoading ? (
								<Loader2 className="w-4 h-4 animate-spin mr-1" />
							) : (
								<Search className="w-4 h-4 mr-1" />
							)}
							Lookup
						</Button>
					</div>
					{lookupResult && (
						<div className="mt-3 border rounded-lg p-3 space-y-1 text-sm">
							<div className="flex items-center justify-between">
								<span className="font-mono font-bold">{lookupResult.code}</span>
								<div className="flex gap-1">
									<Button
										size="icon"
										variant="ghost"
										className="w-6 h-6"
										onClick={() => copyCode(lookupResult.code)}
										title="Copy code"
									>
										<Copy className="w-3 h-3" />
									</Button>
								</div>
							</div>
							<div className="flex justify-between">
								<span className="text-muted-foreground">Status</span>
								<Badge
									variant={lookupResult.active ? "default" : "destructive"}
								>
									{lookupResult.active ? "Active" : "Voided"}
								</Badge>
							</div>
							<div className="flex justify-between">
								<span className="text-muted-foreground">Initial Balance</span>
								<span>
									${Number(lookupResult.initial_balance ?? 0).toFixed(2)}
								</span>
							</div>
							<div className="flex justify-between">
								<span className="text-muted-foreground">Remaining Balance</span>
								<span className="font-bold text-green-600">
									${Number(lookupResult.remaining_balance ?? 0).toFixed(2)}
								</span>
							</div>
							<div className="flex justify-between">
								<span className="text-muted-foreground">Customer</span>
								<span>{lookupResult.customer_name || "—"}</span>
							</div>
							{lookupResult.expires_at > 0 && (
								<div className="flex justify-between">
									<span className="text-muted-foreground">Expires</span>
									<span>
										{new Date(lookupResult.expires_at).toLocaleDateString()}
									</span>
								</div>
							)}
							{lookupResult.notes && (
								<div className="flex justify-between">
									<span className="text-muted-foreground">Notes</span>
									<span>{lookupResult.notes}</span>
								</div>
							)}
							<div className="flex justify-between">
								<span className="text-muted-foreground">Created</span>
								<span>
									{new Date(lookupResult.created_at).toLocaleString()}
								</span>
							</div>
						</div>
					)}
				</CardContent>
			</Card>

			{/* ── Filter tabs ── */}
			<div className="flex gap-2">
				{["", "true", "false"].map((f) => (
					<Button
						key={f}
						variant={filter === f ? "default" : "outline"}
						size="sm"
						onClick={() => setFilter(f)}
					>
						{f === "" ? "All" : f === "true" ? "Active" : "Voided"}
					</Button>
				))}
			</div>

			{/* ── Gift card list ── */}
			{isLoading ? (
				<div className="flex justify-center py-10">
					<Loader2 className="w-6 h-6 animate-spin" />
				</div>
			) : giftCards.length === 0 ? (
				<Card>
					<CardContent className="p-6 text-center text-muted-foreground">
						<Gift className="w-8 h-8 mx-auto mb-2 opacity-50" />
						<p>No gift cards found</p>
					</CardContent>
				</Card>
			) : (
				<div className="space-y-2">
					{giftCards.map((card) => (
						<Card key={card.id} className="hover:bg-accent/30">
							<CardContent className="p-4">
								<div className="flex items-center justify-between">
									<div className="flex-1">
										<div className="flex items-center gap-2">
											<span className="font-mono font-bold text-sm">
												{card.code}
											</span>
											<Button
												size="icon"
												variant="ghost"
												className="w-5 h-5"
												onClick={() => copyCode(card.code)}
												title="Copy code"
											>
												<Copy className="w-3 h-3" />
											</Button>
											<Badge
												variant={card.active ? "default" : "destructive"}
												className="text-xs"
											>
												{card.active ? "Active" : "Voided"}
											</Badge>
										</div>
										<div className="text-xs text-muted-foreground mt-1 flex gap-4">
											<span>
												Customer:{" "}
												<span className="font-medium">
													{card.customer_name || "—"}
												</span>
											</span>
											<span>
												Created:{" "}
												<span className="font-medium">
													{new Date(card.created_at).toLocaleDateString()}
												</span>
											</span>
										</div>
									</div>
									<div className="text-right flex items-center gap-3">
										<div>
											<p className="text-xs text-muted-foreground">Balance</p>
											<p className="font-bold text-sm">
												${Number(card.remaining_balance ?? 0).toFixed(2)}
											</p>
											<p className="text-xs text-muted-foreground">
												of ${Number(card.initial_balance ?? 0).toFixed(2)}
											</p>
										</div>
										{card.active && (
											<Button
												size="sm"
												variant="outline"
												className="text-red-500 border-red-500/30 hover:bg-red-500/10"
												onClick={() => {
													if (
														confirm(
															`Void gift card ${card.code}? This cannot be undone.`,
														)
													) {
														voidMutation.mutate(card.id);
													}
												}}
												disabled={voidMutation.isPending}
											>
												<Ban className="w-3 h-3 mr-1" />
												Void
											</Button>
										)}
									</div>
								</div>
							</CardContent>
						</Card>
					))}
				</div>
			)}
		</div>
	);
}
