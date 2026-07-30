import { useState, useRef } from "react";
import { api } from "../lib/api";
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

export default function ImportExportPage() {
  const [exportEntity, setExportEntity] = useState("customers");
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
    api.export.csv(exportEntity);
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
    } catch (e: any) {
      setResult({ imported: 0, errors: [e.message || "Import failed"] });
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
          <Download className="w-5 h-5 text-blue-400" />
          Export Data
        </h2>
        <p className="text-sm text-slate-400 mb-4">
          Download all records from any entity type as a CSV file.
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={exportEntity}
            onChange={(e) => setExportEntity(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
          >
            {ENTITIES.map((e) => (
              <option key={e.id} value={e.id}>
                {e.label}
              </option>
            ))}
          </select>
          <Button onClick={handleExport} className="flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export CSV
          </Button>
        </div>
      </Card>

      {/* ── Import Section ── */}
      <Card className="p-5">
        <h2 className="text-lg font-semibold mb-1 flex items-center gap-2">
          <Upload className="w-5 h-5 text-green-400" />
          Import Data
        </h2>
        <p className="text-sm text-slate-400 mb-4">
          Upload a CSV file to bulk-import customers or products. The first row
          must contain column headers.
        </p>
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-3 flex-wrap">
            <select
              value={importType}
              onChange={(e) => {
                setImportType(e.target.value as "customers" | "products");
                setResult(null);
              }}
              className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="customers">Customers</option>
              <option value="products">Products</option>
            </select>

            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
            />
            <Button
              variant="secondary"
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-2"
            >
              <FileUp className="w-4 h-4" />
              {file ? file.name : "Choose CSV File"}
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
            <summary className="text-sm text-slate-500 cursor-pointer hover:text-slate-300">
              Required CSV columns
            </summary>
            <div className="mt-2 text-xs text-slate-400 space-y-2">
              <div>
                <strong className="text-slate-300">Customers:</strong>{" "}
                <code className="text-blue-300">first_name</code>,{" "}
                <code className="text-blue-300">last_name</code> (required).
                Optional: <code className="text-slate-400">email</code>,{" "}
                <code className="text-slate-400">phone</code>,{" "}
                <code className="text-slate-400">mobile</code>,{" "}
                <code className="text-slate-400">company</code>,{" "}
                <code className="text-slate-400">address_line1</code>,{" "}
                <code className="text-slate-400">city</code>,{" "}
                <code className="text-slate-400">state</code>,{" "}
                <code className="text-slate-400">zip</code>,{" "}
                <code className="text-slate-400">notes</code>,{" "}
                <code className="text-slate-400">tags</code>.
              </div>
              <div>
                <strong className="text-slate-300">Products:</strong>{" "}
                <code className="text-blue-300">name</code> (required).
                Optional: <code className="text-slate-400">sku</code>,{" "}
                <code className="text-slate-400">price</code>,{" "}
                <code className="text-slate-400">cost</code>,{" "}
                <code className="text-slate-400">quantity_on_hand</code>,{" "}
                <code className="text-slate-400">description</code>,{" "}
                <code className="text-slate-400">category</code>,{" "}
                <code className="text-slate-400">min_stock</code>,{" "}
                <code className="text-slate-400">location</code>.
              </div>
            </div>
          </details>
        </div>
      </Card>
    </div>
  );
}
