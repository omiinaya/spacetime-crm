import { useState, useRef } from "react";
import { api } from "../lib/api";
import type { ExportFormat } from "../lib/api/export";
import {
	Download,
	Upload,
	FileUp,
	CheckCircle,
	AlertCircle,
	Loader2,
} from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";

const ENTITIES = [
	{ id: "customers", label: "Customers" },
	{ id: "tickets", label: "Tickets" },
	{ id: "invoices", label: "Invoices" },
	{ id: "payments", label: "Payments" },
	{ id: "appointments", label: "Appointments" },
	{ id: "products", label: "Products" },
	{ id: "estimates", label: "Estimates" },
	{ id: "purchase_orders", label: "Purchase Orders" },
	{ id: "tax_rates", label: "Tax Rates" },
	{ id: "users", label: "Users" },
];

const EXPORT_FORMATS: { id: ExportFormat; label: string }[] = [
	{ id: "csv", label: "CSV" },
	{ id: "xlsx", label: "XLSX" },
	{ id: "json", label: "JSON" },
];

export default function ImportExportPage() {
	const [exportEntity, setExportEntity] = useState("customers");
	const [exportFormat, setExportFormat] = useState<ExportFormat>("csv");
	const [importType, setImportType] = useState<"customers" | "products">(
		"customers",
	);
	const [file, setFile] = useState<File | null>(null);
	const [importing, setImporting] = useState(false);
	const [result, setResult] = useState<{
		imported: number;
		errors: string[];
	} | null>(null);
	const fileRef = useRef<HTMLInputElement>(null);

	const handleExport = () => {
		api.export[exportFormat](exportEntity);
	};

	const handleImport = async () => {
		if (!file) return;
		setImporting(true);
		setResult(null);
		try {
			const res = await (importType === "customers"
				? api.import.customers(file)
				: api.import.products(file));
			setResult(res);
		} catch (e: unknown) {
			setResult({
				imported: 0,
				errors: [(e as Error).message || "Import failed"],
			});
		} finally {
			setImporting(false);
		}
	};

	const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const f = e.target.files?.[0] || null;
		setFile(f);
		setResult(null);
	};

	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold">Import / Export</h1>

			{/* ── Export Section ── */}
			<Card className="p-5">
				<h2 className="text-lg font-semibold mb-1 flex items-center gap-2">
					<Download className="w-5 h-5 text-primary" />
					Export Data
				</h2>
				<p className="text-sm text-muted-foreground mb-4">
					Download all records from any entity type as CSV, XLSX or JSON.
				</p>
				<div className="flex items-center gap-3 flex-wrap">
					<select
						value={exportEntity}
						onChange={(e) => setExportEntity(e.target.value)}
						className="bg-muted border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
					>
						{ENTITIES.map((e) => (
							<option key={e.id} value={e.id}>
								{e.label}
							</option>
						))}
					</select>
					<select
						value={exportFormat}
						onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
						className="bg-muted border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
					>
						{EXPORT_FORMATS.map((f) => (
							<option key={f.id} value={f.id}>
								{f.label}
							</option>
						))}
					</select>
					<Button onClick={handleExport} className="flex items-center gap-2">
						<Download className="w-4 h-4" />
						Export {exportFormat.toUpperCase()}
					</Button>
				</div>
			</Card>

			{/* ── Import Section ── */}
			<Card className="p-5">
				<h2 className="text-lg font-semibold mb-1 flex items-center gap-2">
					<Upload className="w-5 h-5 text-green-400" />
					Import Data
				</h2>
				<p className="text-sm text-muted-foreground mb-4">
					Upload a CSV, XLSX or JSON file to bulk-import customers or products.
					The format is detected automatically.
				</p>
				<div className="flex flex-col gap-3">
					<div className="flex items-center gap-3 flex-wrap">
						<select
							value={importType}
							onChange={(e) => {
								setImportType(e.target.value as "customers" | "products");
								setResult(null);
							}}
							className="bg-muted border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
						>
							<option value="customers">Customers</option>
							<option value="products">Products</option>
						</select>

						<input
							ref={fileRef}
							type="file"
							accept=".csv,.xlsx,.json"
							onChange={handleFileChange}
							className="hidden"
						/>
						<Button
							variant="secondary"
							onClick={() => fileRef.current?.click()}
							className="flex items-center gap-2"
						>
							<FileUp className="w-4 h-4" />
							{file ? file.name : "Choose File"}
						</Button>

						<Button
							onClick={handleImport}
							disabled={!file || importing}
							className="flex items-center gap-2"
						>
							{importing ? (
								<Loader2 className="w-4 h-4 animate-spin" />
							) : (
								<Upload className="w-4 h-4" />
							)}
							{importing ? "Importing..." : "Import"}
						</Button>
					</div>

					{/* ── Import Result ── */}
					{result && (
						<div
							className={`mt-3 p-3 rounded border ${result.errors.length > 0 ? "border-amber-700 bg-amber-900/20" : "border-green-700 bg-green-900/20"}`}
						>
							<div className="flex items-center gap-2 mb-1">
								{result.errors.length > 0 ? (
									<AlertCircle className="w-4 h-4 text-amber-400" />
								) : (
									<CheckCircle className="w-4 h-4 text-green-400" />
								)}
								<span className="font-medium">
									Imported {result.imported} record
									{result.imported !== 1 ? "s" : ""}
								</span>
							</div>
							{result.errors.length > 0 && (
								<ul className="mt-2 text-sm text-amber-300 space-y-1 max-h-40 overflow-y-auto">
									{result.errors.map((err, i) => (
										<li key={i} className="font-mono text-xs">
											{err}
										</li>
									))}
								</ul>
							)}
						</div>
					)}

					{/* ── Column Reference ── */}
					<details className="mt-2">
						<summary className="text-sm text-muted-foreground cursor-pointer hover:text-foreground/80">
							Required columns (CSV header / XLSX first row / JSON keys)
						</summary>
						<div className="mt-2 text-xs text-muted-foreground space-y-2">
							<div>
								<strong className="text-foreground/80">Customers:</strong>{" "}
								<code className="text-primary/80">first_name</code>,{" "}
								<code className="text-primary/80">last_name</code> (required).
								Optional: <code className="text-muted-foreground">email</code>,{" "}
								<code className="text-muted-foreground">phone</code>,{" "}
								<code className="text-muted-foreground">mobile</code>,{" "}
								<code className="text-muted-foreground">company</code>,{" "}
								<code className="text-muted-foreground">address_line1</code>,{" "}
								<code className="text-muted-foreground">city</code>,{" "}
								<code className="text-muted-foreground">state</code>,{" "}
								<code className="text-muted-foreground">zip</code>,{" "}
								<code className="text-muted-foreground">notes</code>,{" "}
								<code className="text-muted-foreground">tags</code>.
							</div>
							<div>
								<strong className="text-foreground/80">Products:</strong>{" "}
								<code className="text-primary/80">name</code> (required).
								Optional: <code className="text-muted-foreground">sku</code>,{" "}
								<code className="text-muted-foreground">price</code>,{" "}
								<code className="text-muted-foreground">cost</code>,{" "}
								<code className="text-muted-foreground">quantity_on_hand</code>,{" "}
								<code className="text-muted-foreground">description</code>,{" "}
								<code className="text-muted-foreground">category</code>,{" "}
								<code className="text-muted-foreground">min_stock</code>,{" "}
								<code className="text-muted-foreground">location</code>.
							</div>
							<div>
								<strong className="text-foreground/80">JSON format:</strong> a JSON
								array of objects, one per record, using the same keys as the
								columns above, e.g.{" "}
								<code className="text-muted-foreground">
									[{"{"}"first_name": "Alice", "last_name": "Smith"{"}"}]
								</code>
								.
							</div>
						</div>
					</details>
				</div>
			</Card>
		</div>
	);
}
