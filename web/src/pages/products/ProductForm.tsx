import { useRef } from "react";
import { Button } from "../../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Scan, ScanLine } from "lucide-react";

interface ProductFormData {
	name?: string;
	sku?: string;
	barcode?: string;
	description?: string;
	category?: string;
	price?: number;
	cost?: number;
	quantity_on_hand?: number;
	min_stock?: number;
	reorder_quantity?: number;
	location?: string;
}

interface ProductFormProps {
	showForm: boolean;
	form: ProductFormData;
	setForm: (f: ProductFormData) => void;
	editId: string | null;
	handleSubmit: () => void;
	scanning: boolean;
	startScanner: () => void;
	stopScanner: () => void;
	videoRef: React.RefObject<HTMLVideoElement>;
	barcodeDetectorSupported: boolean;
	setShowForm: (v: boolean) => void;
	setEditId: (v: string | null) => void;
}

export default function ProductForm({
	showForm,
	form,
	setForm,
	editId,
	handleSubmit,
	scanning,
	startScanner,
	stopScanner,
	videoRef,
	barcodeDetectorSupported,
	setShowForm,
	setEditId,
}: ProductFormProps) {
	if (!showForm) return null;

	return (
		<Card className="border-primary/30">
			<CardHeader>
				<CardTitle>{editId ? "Edit Product" : "New Product"}</CardTitle>
			</CardHeader>
			<CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<Input
					placeholder="Name"
					value={form.name}
					onChange={(e) => setForm({ ...form, name: e.target.value })}
				/>
				<Input
					placeholder="SKU"
					value={form.sku}
					onChange={(e) => setForm({ ...form, sku: e.target.value })}
				/>
				<div className="col-span-2">
					<Input
						placeholder="Description"
						value={form.description}
						onChange={(e) => setForm({ ...form, description: e.target.value })}
					/>
				</div>
				<Input
					placeholder="Category"
					value={form.category}
					onChange={(e) => setForm({ ...form, category: e.target.value })}
				/>
				<Input
					placeholder="Price"
					type="number"
					value={form.price}
					onChange={(e) =>
						setForm({ ...form, price: parseFloat(e.target.value) || 0 })
					}
				/>
				<Input
					placeholder="Cost"
					type="number"
					value={form.cost}
					onChange={(e) =>
						setForm({ ...form, cost: parseFloat(e.target.value) || 0 })
					}
				/>
				<Input
					placeholder="Qty on hand"
					type="number"
					value={form.quantity_on_hand}
					onChange={(e) =>
						setForm({
							...form,
							quantity_on_hand: parseFloat(e.target.value) || 0,
						})
					}
				/>
				<Input
					placeholder="Min stock"
					type="number"
					value={form.min_stock ?? 0}
					onChange={(e) =>
						setForm({ ...form, min_stock: parseFloat(e.target.value) || 0 })
					}
				/>
				<Input
					placeholder="Reorder qty"
					type="number"
					value={form.reorder_quantity ?? 0}
					onChange={(e) =>
						setForm({
							...form,
							reorder_quantity: parseFloat(e.target.value) || 0,
						})
					}
				/>
				<Input
					placeholder="Location"
					value={form.location ?? ""}
					onChange={(e) => setForm({ ...form, location: e.target.value })}
				/>
				<div className="col-span-2 flex gap-2">
					<div className="flex-1 flex gap-2">
						<Input
							placeholder="Barcode"
							value={form.barcode}
							onChange={(e) => setForm({ ...form, barcode: e.target.value })}
							className="flex-1"
						/>
						{barcodeDetectorSupported && (
							<Button
								type="button"
								variant="outline"
								size="icon"
								onClick={startScanner}
								title="Scan barcode"
							>
								<Scan className="h-4 w-4" />
							</Button>
						)}
					</div>
				</div>
				{scanning && (
					<div className="col-span-2 relative rounded-lg overflow-hidden bg-black">
						<video ref={videoRef} className="w-full h-48 object-cover" />
						<div className="absolute inset-0 flex items-center justify-center pointer-events-none">
							<ScanLine className="h-16 w-16 text-white/40" />
						</div>
						<Button
							size="sm"
							variant="outline"
							className="absolute top-2 right-2 bg-black/50 text-white border-white/30"
							onClick={stopScanner}
						>
							Cancel
						</Button>
						<p className="absolute bottom-2 left-2 text-xs text-white/60 bg-black/40 px-2 py-1 rounded">
							Point camera at barcode
						</p>
					</div>
				)}
				<div className="col-span-2 flex gap-2">
					<Button onClick={handleSubmit}>{editId ? "Update" : "Create"}</Button>
					<Button
						variant="outline"
						onClick={() => {
							setShowForm(false);
							setEditId(null);
						}}
					>
						Cancel
					</Button>
				</div>
			</CardContent>
		</Card>
	);
}
