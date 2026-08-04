import { Search, Plus, Banknote, CreditCard } from "lucide-react";
import { Button } from "../../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../components/ui/card";
import { Input } from "../../components/ui/input";

interface SearchProduct {
	id: string;
	name: string;
	sku: string;
	price: number;
	quantity_on_hand?: number;
}

interface CustomerResult {
	id: string;
	first_name?: string;
	last_name?: string;
	email?: string;
	phone?: string;
}

interface ProductSearchProps {
	searchQuery: string;
	setSearchQuery: (val: string) => void;
	searchResults: SearchProduct[] | undefined;
	addToCart: (product: {
		id: string;
		name: string;
		sku: string;
		price: number;
	}) => void;
	scanRef: React.RefObject<HTMLInputElement>;
	customerSearch: string;
	setCustomerSearch: (val: string) => void;
	customerResults: CustomerResult[] | undefined;
	customerName: string;
	setCustomerName: (val: string) => void;
	setCustomerId: (val: string) => void;
	taxRate: string;
	setTaxRate: (val: string) => void;
	discount: string;
	setDiscount: (val: string) => void;
	paymentMethod: "cash" | "card";
	setPaymentMethod: (val: "cash" | "card") => void;
}

export default function ProductSearch({
	searchQuery,
	setSearchQuery,
	searchResults,
	addToCart,
	scanRef,
	customerSearch,
	setCustomerSearch,
	customerResults,
	setCustomerName,
	setCustomerId,
	taxRate,
	setTaxRate,
	discount,
	setDiscount,
	paymentMethod,
	setPaymentMethod,
}: ProductSearchProps) {
	return (
		<div className="lg:col-span-2 space-y-4">
			<Card>
				<CardHeader className="pb-2">
					<CardTitle className="text-sm flex items-center gap-2">
						<Search className="w-4 h-4" /> Scan or Search Products
					</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="relative">
						<Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
						<Input
							ref={scanRef}
							placeholder="Scan barcode or search products..."
							className="pl-9 text-lg"
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							autoFocus
						/>
					</div>

					{searchQuery.length >= 1 && searchResults && (
						<div className="mt-2 border rounded-lg divide-y max-h-60 overflow-y-auto">
							{searchResults.length === 0 ? (
								<p className="p-3 text-sm text-muted-foreground">
									No products found
								</p>
							) : (
								searchResults.slice(0, 10).map((product) => (
									<div
										key={product.id}
										className="flex items-center justify-between p-3 hover:bg-accent cursor-pointer"
										onClick={() => addToCart(product)}
									>
										<div>
											<p className="font-medium">{product.name}</p>
											<p className="text-xs text-muted-foreground">
												{product.sku} &middot; Stock:{" "}
												{product.quantity_on_hand ?? 0}
											</p>
										</div>
										<div className="flex items-center gap-2">
											<p className="font-semibold">
												${product.price.toFixed(2)}
											</p>
											<Button size="icon" variant="ghost" className="w-7 h-7" aria-label="Add to cart">
												<Plus className="w-3 h-3" />
											</Button>
										</div>
									</div>
								))
							)}
						</div>
					)}
				</CardContent>
			</Card>

			{/* Quick customer / tender controls */}
			<Card>
				<CardHeader className="pb-2">
					<CardTitle className="text-sm">Sale Details</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
						<div className="relative">
							<label className="text-xs text-muted-foreground mb-1 block">
								Customer
							</label>
							<Input
								value={customerSearch}
								onChange={(e) => {
									setCustomerSearch(e.target.value);
									if (!e.target.value) {
										setCustomerId("");
										setCustomerName("Walk-in");
									}
								}}
								placeholder="Search customers..."
							/>
							{customerSearch.length >= 1 &&
								customerResults &&
								customerResults.length > 0 && (
									<div className="absolute z-50 top-full left-0 right-0 bg-card border rounded-lg mt-1 shadow-lg max-h-48 overflow-y-auto">
										{customerResults.map((c) => (
											<div
												key={c.id}
												className="flex items-center justify-between p-2 hover:bg-accent cursor-pointer text-sm"
												onClick={() => {
													setCustomerId(c.id);
													setCustomerName(
														`${c.first_name} ${c.last_name}`.trim(),
													);
													setCustomerSearch("");
												}}
											>
												<span className="font-medium">
													{c.first_name && c.last_name
														? `${c.first_name} ${c.last_name}`
														: c.email || "Unknown"}
												</span>
												<span className="text-xs text-muted-foreground">
													{c.email || c.phone || ""}
												</span>
											</div>
										))}
									</div>
								)}
							{customerSearch.length > 0 &&
								customerResults &&
								customerResults.length === 0 && (
									<p className="text-xs text-muted-foreground mt-1">
										No customers found
									</p>
								)}
						</div>
						<div>
							<label className="text-xs text-muted-foreground mb-1 block">
								Tax Rate %
							</label>
							<Input
								value={taxRate}
								onChange={(e) => setTaxRate(e.target.value)}
								type="number"
								step="0.01"
							/>
						</div>
						<div>
							<label className="text-xs text-muted-foreground mb-1 block">
								Discount $
							</label>
							<Input
								value={discount}
								onChange={(e) => setDiscount(e.target.value)}
								type="number"
								step="0.01"
							/>
						</div>
						<div>
							<label className="text-xs text-muted-foreground mb-1 block">
								Payment
							</label>
							<div className="flex gap-1">
								<Button
									size="sm"
									variant={paymentMethod === "cash" ? "default" : "outline"}
									className="flex-1 text-xs"
									onClick={() => setPaymentMethod("cash")}
								>
									<Banknote className="w-3 h-3 mr-1" /> Cash
								</Button>
								<Button
									size="sm"
									variant={paymentMethod === "card" ? "default" : "outline"}
									className="flex-1 text-xs"
									onClick={() => setPaymentMethod("card")}
								>
									<CreditCard className="w-3 h-3 mr-1" /> Card
								</Button>
							</div>
						</div>
					</div>
				</CardContent>
			</Card>
		</div>
	);
}
