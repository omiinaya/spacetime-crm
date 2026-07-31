import { Button } from "../../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Select } from "../../components/ui/select";
import type { UseMutationResult } from "@tanstack/react-query";

interface InvoiceFormCustomer {
	id: string;
	first_name?: string;
	last_name?: string;
}

interface InvoiceFormData {
	customer_id: string;
	ticket_id: string;
	notes: string;
	terms: string;
	due_date: string;
	currency: string;
}

interface InvoiceFormProps {
	showForm: boolean;
	form: InvoiceFormData;
	setForm: (f: InvoiceFormData) => void;
	customers: InvoiceFormCustomer[];
	createMutation: UseMutationResult<{ ok: boolean }, Error, void, unknown>;
	setShowForm: (v: boolean) => void;
	DRAFT_KEY: string;
}

export default function InvoiceForm({
	showForm,
	form,
	setForm,
	customers,
	createMutation,
	setShowForm,
	DRAFT_KEY,
}: InvoiceFormProps) {
	if (!showForm) return null;

	return (
		<Card className="border-primary/30">
			<CardHeader>
				<CardTitle>New Invoice</CardTitle>
			</CardHeader>
			<CardContent className="space-y-3">
				<Select
					value={form.customer_id}
					onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
				>
					<option value="">Select customer...</option>
					{customers.map((c) => (
						<option key={c.id} value={c.id}>
							{c.first_name} {c.last_name}
						</option>
					))}
				</Select>
				<Input
					placeholder="Ticket ID (optional)"
					value={form.ticket_id}
					onChange={(e) => setForm({ ...form, ticket_id: e.target.value })}
				/>
				<Input
					placeholder="Notes"
					value={form.notes}
					onChange={(e) => setForm({ ...form, notes: e.target.value })}
				/>
				<Input
					placeholder="Terms"
					value={form.terms}
					onChange={(e) => setForm({ ...form, terms: e.target.value })}
				/>
				<Input
					type="date"
					value={form.due_date}
					onChange={(e) => setForm({ ...form, due_date: e.target.value })}
				/>
				<Select
					value={form.currency}
					onChange={(e) => setForm({ ...form, currency: e.target.value })}
				>
					<option value="USD">USD ($)</option>
					<option value="EUR">EUR (€)</option>
					<option value="GBP">GBP (£)</option>
					<option value="CAD">CAD (C$)</option>
					<option value="AUD">AUD (A$)</option>
					<option value="JPY">JPY (¥)</option>
				</Select>
				<div className="flex gap-2">
					<Button
						onClick={() => createMutation.mutate()}
						disabled={createMutation.isPending}
					>
						Create
					</Button>
					<Button
						variant="outline"
						onClick={() => {
							setShowForm(false);
							localStorage.removeItem(DRAFT_KEY);
						}}
					>
						Cancel
					</Button>
				</div>
			</CardContent>
		</Card>
	);
}
