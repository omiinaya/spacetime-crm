import { Button } from "../../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Select } from "../../components/ui/select";
import { Textarea } from "../../components/ui/textarea";
import { Badge } from "../../components/ui/badge";
import Pagination from "../../components/Pagination";
import { Plus, Mail, Edit3, CheckSquare, Square } from "lucide-react";
import type { UseMutationResult } from "@tanstack/react-query";
import type {
	Invoice,
	Customer,
	TaxRate,
	InvoiceLineItem,
	InvoiceSummary,
} from "../../lib/api";

const statusColors: Record<
	string,
	"default" | "warning" | "success" | "destructive" | "outline"
> = {
	draft: "outline",
	sent: "default",
	paid: "success",
	partial: "warning",
	overdue: "destructive",
	cancelled: "outline",
};

interface InvoiceListProps {
	filter: string;
	setFilter: (val: string) => void;
	summary: InvoiceSummary | undefined;
	invoices: Invoice[];
	customers: Customer[];
	selectedInv: Invoice | null;
	selectInvoice: (inv: Invoice) => void;
	selectedIds: Set<string>;
	toggleSelect: (id: string) => void;
	toggleSelectAll: () => void;
	setSelectedIds: (ids: Set<string>) => void;
	sendReminderMutation: UseMutationResult;
	selectedIdsSize: number;
	showBulkEdit: boolean;
	setShowBulkEdit: (v: boolean) => void;
	bulkStatus: string;
	setBulkStatus: (v: string) => void;
	bulkMutation: UseMutationResult;
	batchEmailMutation: UseMutationResult;
	bulkEditMutation: UseMutationResult;
	bulkEditForm: { terms: string; notes: string };
	setBulkEditForm: (f: { terms: string; notes: string }) => void;
	pag: any;
	statusMutation: UseMutationResult;
	taxMutation: UseMutationResult;
	taxRates: TaxRate[];
	lineItems: InvoiceLineItem[];
	newItem: {
		description: string;
		quantity: number;
		unit_price: number;
		item_type: string;
	};
	setNewItem: (item: {
		description: string;
		quantity: number;
		unit_price: number;
		item_type: string;
	}) => void;
	addLineItem: () => void;
	removeLineItem: (itemId: string) => void;
	setSelectedInv: (inv: Invoice | null) => void;
	handleSendEmail: () => void;
	sendEmailMutation: UseMutationResult;
	showPaymentForm: boolean;
	setShowPaymentForm: (v: boolean) => void;
	paymentForm: { amount: number; method: string; reference: string };
	setPaymentForm: (f: {
		amount: number;
		method: string;
		reference: string;
	}) => void;
	recordPaymentMutation: UseMutationResult;
	selectedInvCurrency: string;
	selectedInvTotal: number;
	selectedInvSubtotal: number;
	selectedInvTaxRate: number;
}

export default function InvoiceList({
	filter,
	setFilter,
	summary,
	invoices,
	customers,
	selectedInv,
	selectInvoice,
	selectedIds,
	toggleSelect,
	toggleSelectAll,
	setSelectedIds,
	sendReminderMutation,
	selectedIdsSize,
	showBulkEdit,
	setShowBulkEdit,
	bulkStatus,
	setBulkStatus,
	bulkMutation,
	batchEmailMutation,
	bulkEditMutation,
	bulkEditForm,
	setBulkEditForm,
	pag,
	statusMutation,
	taxMutation,
	taxRates,
	lineItems,
	newItem,
	setNewItem,
	addLineItem,
	removeLineItem,
	setSelectedInv,
	handleSendEmail,
	sendEmailMutation,
	showPaymentForm,
	setShowPaymentForm,
	paymentForm,
	setPaymentForm,
	recordPaymentMutation,
	selectedInvCurrency,
	selectedInvTotal,
	selectedInvSubtotal,
	selectedInvTaxRate,
}: InvoiceListProps) {
	return (
		<>
			{/* Filter buttons */}
			<div className="flex gap-2 flex-wrap">
				{["", "draft", "sent", "paid", "overdue", "cancelled"].map((s) => (
					<Button
						key={s}
						size="sm"
						variant={filter === s ? "default" : "outline"}
						onClick={() => setFilter(s)}
					>
						{s || "All"}
					</Button>
				))}
			</div>

			{/* Summary bar */}
			{summary && (
				<div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
					<div className="border rounded-lg p-3">
						<p className="text-xs text-muted-foreground">Total</p>
						<p className="text-lg font-bold">{summary.total_count}</p>
					</div>
					<div className="border rounded-lg p-3">
						<p className="text-xs text-muted-foreground">Outstanding</p>
						<p className="text-lg font-bold text-amber-400">
							${summary.total_outstanding.toFixed(2)}
						</p>
					</div>
					<div className="border rounded-lg p-3 relative">
						<p className="text-xs text-muted-foreground">Overdue</p>
						<p className="text-lg font-bold text-red-400">
							{summary.overdue_count} / ${summary.overdue_total.toFixed(2)}
						</p>
						{summary.overdue_count > 0 && (
							<Button
								size="sm"
								variant="ghost"
								className="absolute top-1 right-1 h-6 text-[10px] text-red-400 hover:text-red-300 hover:bg-red-950/30"
								onClick={() => sendReminderMutation.mutate(undefined as any)}
								disabled={sendReminderMutation.isPending}
							>
								{sendReminderMutation.isPending ? (
									<span className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full" />
								) : (
									"Remind"
								)}
							</Button>
						)}
					</div>
					<div className="border rounded-lg p-3">
						<p className="text-xs text-muted-foreground">Revenue</p>
						<p className="text-lg font-bold text-green-400">
							${summary.total_revenue.toFixed(2)}
						</p>
					</div>
				</div>
			)}

			{/* Bulk action bar */}
			{selectedIdsSize > 0 && (
				<div className="flex items-center gap-2 p-3 rounded-lg border border-primary/30 bg-primary/5">
					<span className="text-sm font-medium">
						{selectedIdsSize} selected
					</span>
					<div className="flex-1" />
					<Select
						value={bulkStatus}
						onChange={(e) => setBulkStatus(e.target.value)}
						className="w-28"
					>
						<option value="draft">Draft</option>
						<option value="sent">Sent</option>
						<option value="paid">Paid</option>
						<option value="overdue">Overdue</option>
						<option value="cancelled">Cancelled</option>
					</Select>
					<Button
						size="sm"
						onClick={() => bulkMutation.mutate(undefined as any)}
						disabled={bulkMutation.isPending}
					>
						{bulkMutation.isPending ? (
							<span className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full mr-1" />
						) : null}
						Apply
					</Button>
					<Button
						size="sm"
						variant="outline"
						onClick={() => batchEmailMutation.mutate(undefined as any)}
						disabled={batchEmailMutation.isPending}
					>
						{batchEmailMutation.isPending ? (
							<span className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full mr-1" />
						) : (
							<Mail className="h-3.5 w-3.5 mr-1" />
						)}
						Email Selected
					</Button>
					<Button
						size="sm"
						variant="outline"
						onClick={() => {
							setBulkEditForm({ terms: "", notes: "" });
							setShowBulkEdit(true);
						}}
					>
						<Edit3 className="h-3.5 w-3.5 mr-1" />
						Edit
					</Button>
					<Button
						size="sm"
						variant="ghost"
						onClick={() => setSelectedIds(new Set())}
					>
						Clear
					</Button>
				</div>
			)}

			{/* Invoice list + detail */}
			<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
				<div className={`space-y-3 ${selectedInv ? "hidden lg:block" : ""}`}>
					{/* Select all header */}
					{invoices.length > 0 && (
						<div className="flex items-center gap-2 px-1 pb-1 text-xs text-muted-foreground">
							<button
								onClick={toggleSelectAll}
								className="flex items-center gap-1.5 hover:text-foreground"
							>
								{selectedIds.size === invoices.length ? (
									<CheckSquare className="h-3.5 w-3.5" />
								) : (
									<Square className="h-3.5 w-3.5" />
								)}
								{selectedIds.size === invoices.length
									? "Deselect all"
									: "Select all"}
							</button>
							{selectedIds.size > 0 && (
								<span className="text-primary font-medium">
									{selectedIds.size} selected
								</span>
							)}
						</div>
					)}
					{invoices.map((inv) => {
						const cust = customers.find((c) => c.id === inv.customer_id);
						return (
							<div key={inv.id} className="flex items-start gap-2">
								<button
									onClick={(e) => {
										e.stopPropagation();
										toggleSelect(inv.id);
									}}
									className="mt-4 shrink-0 hover:text-foreground text-muted-foreground"
								>
									{selectedIds.has(inv.id) ? (
										<CheckSquare className="h-4 w-4" />
									) : (
										<Square className="h-4 w-4" />
									)}
								</button>
								<Card
									className={`flex-1 cursor-pointer transition-colors ${selectedInv?.id === inv.id ? "border-primary" : "hover:border-primary/30"} ${inv.status === "overdue" ? "border-l-red-500 border-l-2" : ""}`}
									onClick={() => selectInvoice(inv)}
								>
									<CardContent className="pt-4">
										<div className="flex items-start justify-between">
											<div>
												<div className="flex items-center gap-2">
													<span className="text-xs text-muted-foreground">
														#{inv.invoice_number}
													</span>
													<Badge
														variant={statusColors[inv.status] || "outline"}
													>
														{inv.status}
													</Badge>
												</div>
												<p className="font-medium mt-1">
													{inv.currency || "USD"} {inv.total.toFixed(2)}
												</p>
												{cust && (
													<p className="text-xs text-muted-foreground">
														{cust.first_name} {cust.last_name}
													</p>
												)}
											</div>
										</div>
									</CardContent>
								</Card>
							</div>
						);
					})}
				</div>

				{selectedInv && (
					<div className="space-y-4">
						{/* Back button (mobile) */}
						<button
							onClick={() => setSelectedInv(null)}
							className="lg:hidden text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
						>
							← Back to list
						</button>
						<Card
							className={
								selectedInv.status === "overdue"
									? "border-l-red-500 border-l-2"
									: ""
							}
						>
							<CardHeader>
								<div className="flex items-center justify-between">
									<CardTitle>
										#{selectedInv.invoice_number} — {selectedInvCurrency}{" "}
										{selectedInvTotal.toFixed(2)}
									</CardTitle>
									<div className="flex gap-1">
										<Button
											size="sm"
											variant="outline"
											onClick={handleSendEmail}
											disabled={sendEmailMutation.isPending}
										>
											{sendEmailMutation.isPending ? (
												<span className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full" />
											) : (
												<Mail className="h-3.5 w-3.5 mr-1" />
											)}
											Email
										</Button>
										<Button
											size="sm"
											variant="outline"
											onClick={() =>
												window.open(
													`/api/invoices/${selectedInv.id}/pdf`,
													"_blank",
												)
											}
										>
											<span className="h-3.5 w-3.5 mr-1">📄</span> PDF
										</Button>
									</div>
								</div>
							</CardHeader>
							<CardContent className="space-y-3">
								<Select
									value={selectedInv.status}
									onChange={(e) =>
										statusMutation.mutate({
											id: selectedInv.id,
											status: e.target.value,
										})
									}
								>
									<option value="draft">Draft</option>
									<option value="sent">Sent</option>
									<option value="paid">Paid</option>
									<option value="overdue">Overdue</option>
									<option value="cancelled">Cancelled</option>
								</Select>

								{/* Tax rate selector */}
								<div className="flex items-center gap-2">
									<label className="text-xs text-muted-foreground whitespace-nowrap">
										Tax Rate:
									</label>
									<Select
										value={String(selectedInvTaxRate)}
										onChange={(e) =>
											taxMutation.mutate({
												id: selectedInv.id,
												rate: parseFloat(e.target.value),
											})
										}
										className="flex-1"
									>
										<option value="0">No tax</option>
										{taxRates.map((tr) => (
											<option key={tr.id} value={tr.rate}>
												{tr.name} ({tr.rate}%)
											</option>
										))}
									</Select>
									<span className="text-sm font-medium tabular-nums">
										{selectedInvCurrency}{" "}
										{(
											(selectedInvSubtotal * (selectedInvTaxRate || 0)) /
											100
										).toFixed(2)}
									</span>
								</div>

								{/* Line items */}
								<div className="space-y-2">
									{lineItems.map((li) => (
										<div
											key={li.id}
											className="flex items-center justify-between text-sm p-2 rounded bg-muted/50"
										>
											<div className="min-w-0 flex-1">
												<p className="truncate">{li.description}</p>
												<p className="text-xs text-muted-foreground">
													{li.quantity} x {selectedInvCurrency}{" "}
													{li.unit_price.toFixed(2)}
												</p>
											</div>
											<div className="flex items-center gap-2 shrink-0">
												<span className="font-medium">
													{selectedInvCurrency} {li.total.toFixed(2)}
												</span>
												<Button
													size="icon"
													variant="ghost"
													onClick={() => removeLineItem(li.id)}
												>
													<span className="h-3 w-3">🗑</span>
												</Button>
											</div>
										</div>
									))}
								</div>

								<div className="flex gap-2">
									<select
										value={newItem.item_type}
										onChange={(e) =>
											setNewItem({ ...newItem, item_type: e.target.value })
										}
										className="w-28 h-9 rounded-md border border-input bg-background px-3 text-xs outline-none focus:ring-2 focus:ring-ring"
									>
										<option value="service">Service</option>
										<option value="part">Part</option>
									</select>
									<Input
										placeholder="Description"
										value={newItem.description}
										onChange={(e) =>
											setNewItem({ ...newItem, description: e.target.value })
										}
									/>
									<Input
										type="number"
										placeholder="Qty"
										value={newItem.quantity}
										onChange={(e) =>
											setNewItem({ ...newItem, quantity: +e.target.value })
										}
										className="w-20"
									/>
									<Input
										type="number"
										placeholder="Price"
										value={newItem.unit_price}
										onChange={(e) =>
											setNewItem({ ...newItem, unit_price: +e.target.value })
										}
										className="w-24"
									/>
									<Button size="sm" onClick={addLineItem}>
										<Plus className="h-3 w-3" />
									</Button>
								</div>

								{/* Record Payment */}
								<div className="border-t border-border pt-3 mt-2">
									{!showPaymentForm ? (
										<Button
											variant="outline"
											size="sm"
											className="w-full gap-2"
											onClick={() => setShowPaymentForm(true)}
										>
											<span className="h-4 w-4">💰</span>
											Record Payment
										</Button>
									) : (
										<div className="space-y-2">
											<p className="text-sm font-medium flex items-center gap-2">
												<span className="h-4 w-4">💰</span>
												Record Payment
											</p>
											<div className="flex items-center gap-2">
												<Input
													type="number"
													placeholder="Amount"
													value={paymentForm.amount || selectedInvTotal}
													onChange={(e) =>
														setPaymentForm({
															...paymentForm,
															amount: parseFloat(e.target.value) || 0,
														})
													}
													className="w-28"
												/>
												<Select
													value={paymentForm.method}
													onChange={(e) =>
														setPaymentForm({
															...paymentForm,
															method: e.target.value,
														})
													}
													className="flex-1"
												>
													<option value="cash">Cash</option>
													<option value="card">Card</option>
													<option value="check">Check</option>
													<option value="stripe">Stripe</option>
													<option value="other">Other</option>
												</Select>
											</div>
											<div className="flex items-center gap-2">
												<Input
													placeholder="Reference (optional)"
													value={paymentForm.reference}
													onChange={(e) =>
														setPaymentForm({
															...paymentForm,
															reference: e.target.value,
														})
													}
													className="flex-1"
												/>
												<Button
													size="sm"
													onClick={() =>
														recordPaymentMutation.mutate(undefined as any)
													}
													disabled={recordPaymentMutation.isPending}
												>
													{recordPaymentMutation.isPending ? (
														<span className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full" />
													) : (
														<span className="h-3.5 w-3.5">💳</span>
													)}
													Pay
												</Button>
												<Button
													size="sm"
													variant="ghost"
													onClick={() => setShowPaymentForm(false)}
												>
													Cancel
												</Button>
											</div>
										</div>
									)}
								</div>
							</CardContent>
						</Card>
					</div>
				)}
			</div>

			{/* Bulk Edit dialog */}
			{showBulkEdit && (
				<div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
					<Card className="w-full max-w-lg mx-4">
						<CardHeader>
							<CardTitle>
								Edit {selectedIds.size} Invoice
								{selectedIds.size !== 1 ? "s" : ""}
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-3">
							<div>
								<label className="text-xs text-muted-foreground mb-1 block">
									Terms (leaves empty fields unchanged)
								</label>
								<Textarea
									placeholder="Payment terms..."
									value={bulkEditForm.terms}
									onChange={(e) =>
										setBulkEditForm({ ...bulkEditForm, terms: e.target.value })
									}
								/>
							</div>
							<div>
								<label className="text-xs text-muted-foreground mb-1 block">
									Notes (leaves empty fields unchanged)
								</label>
								<Textarea
									placeholder="Invoice notes..."
									value={bulkEditForm.notes}
									onChange={(e) =>
										setBulkEditForm({ ...bulkEditForm, notes: e.target.value })
									}
								/>
							</div>
							<div className="flex justify-end gap-2 pt-2">
								<Button
									variant="outline"
									onClick={() => setShowBulkEdit(false)}
								>
									Cancel
								</Button>
								<Button
									onClick={() => bulkEditMutation.mutate(undefined as any)}
									disabled={
										bulkEditMutation.isPending ||
										(!bulkEditForm.terms && !bulkEditForm.notes)
									}
								>
									{bulkEditMutation.isPending ? (
										<span className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full mr-1" />
									) : null}
									Apply to {selectedIds.size} invoice
									{selectedIds.size !== 1 ? "s" : ""}
								</Button>
							</div>
						</CardContent>
					</Card>
				</div>
			)}

			<Pagination
				page={pag.page}
				totalPages={pag.totalPages}
				total={pag.total}
				hasPrev={pag.hasPrev}
				hasNext={pag.hasNext}
				onPrev={pag.prevPage}
				onNext={pag.nextPage}
				onGoToPage={pag.goToPage}
			/>
		</>
	);
}
