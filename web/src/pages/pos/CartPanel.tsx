import { ShoppingCart, Minus, Plus, X, Check, Loader2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import type { UseMutationResult } from "@tanstack/react-query";

interface CartItem {
	product_id: string;
	product_name: string;
	sku: string;
	quantity: number;
	unit_price: number;
}

interface CartPanelProps {
	cart: CartItem[];
	updateQty: (productId: string, delta: number) => void;
	subtotal: number;
	taxRate: string;
	taxAmt: number;
	discountAmt: number;
	total: number;
	amountTendered: string;
	setAmountTendered: (val: string) => void;
	tendered: number;
	changeDue: number;
	handleSaleComplete: () => Promise<void>;
	createMutation: UseMutationResult;
	addItemMutation: UseMutationResult;
}

export default function CartPanel({
	cart,
	updateQty,
	subtotal,
	taxRate,
	taxAmt,
	discountAmt,
	total,
	amountTendered,
	setAmountTendered,
	tendered,
	changeDue,
	handleSaleComplete,
	createMutation,
	addItemMutation,
}: CartPanelProps) {
	return (
		<div className="space-y-4">
			<Card className="h-full flex flex-col">
				<CardHeader className="pb-2">
					<CardTitle className="text-sm flex items-center gap-2">
						<ShoppingCart className="w-4 h-4" /> Cart ({cart.length})
					</CardTitle>
				</CardHeader>
				<CardContent className="flex-1 flex flex-col">
					{/* Cart items */}
					<div className="flex-1 space-y-2 max-h-80 overflow-y-auto mb-3">
						{cart.length === 0 ? (
							<p className="text-sm text-muted-foreground text-center py-8">
								Scan or search products to add
							</p>
						) : (
							cart.map((item) => (
								<div
									key={item.product_id}
									className="flex items-center justify-between border rounded-lg p-2"
								>
									<div className="flex-1 min-w-0">
										<p className="text-sm font-medium truncate">
											{item.product_name}
										</p>
										<p className="text-xs text-muted-foreground">
											${item.unit_price.toFixed(2)}
										</p>
									</div>
									<div className="flex items-center gap-1 ml-2">
										<Button
											size="icon"
											variant="ghost"
											className="w-6 h-6"
											onClick={() => updateQty(item.product_id, -1)}
										>
											<Minus className="w-3 h-3" />
										</Button>
										<span className="w-6 text-center text-sm font-medium">
											{item.quantity}
										</span>
										<Button
											size="icon"
											variant="ghost"
											className="w-6 h-6"
											onClick={() => updateQty(item.product_id, 1)}
										>
											<Plus className="w-3 h-3" />
										</Button>
									</div>
									<p className="text-sm font-semibold w-16 text-right">
										${(item.quantity * item.unit_price).toFixed(2)}
									</p>
									<Button
										size="icon"
										variant="ghost"
										className="w-6 h-6 ml-1 text-red-500"
										onClick={() => updateQty(item.product_id, -item.quantity)}
									>
										<X className="w-3 h-3" />
									</Button>
								</div>
							))
						)}
					</div>

					{/* Totals */}
					<div className="border-t pt-3 space-y-1 text-sm">
						<div className="flex justify-between">
							<span>Subtotal</span>
							<span>${subtotal.toFixed(2)}</span>
						</div>
						{parseFloat(taxRate) > 0 && (
							<div className="flex justify-between text-muted-foreground">
								<span>Tax ({taxRate}%)</span>
								<span>${taxAmt.toFixed(2)}</span>
							</div>
						)}
						{discountAmt > 0 && (
							<div className="flex justify-between text-muted-foreground">
								<span>Discount</span>
								<span>-${discountAmt.toFixed(2)}</span>
							</div>
						)}
						<div className="flex justify-between font-bold text-lg pt-1 border-t">
							<span>Total</span>
							<span>${total.toFixed(2)}</span>
						</div>
					</div>

					{/* Tendered & change */}
					<div className="mt-3 space-y-2">
						<Input
							placeholder="Amount tendered"
							value={amountTendered}
							onChange={(e) => setAmountTendered(e.target.value)}
							type="number"
							step="0.01"
						/>
						{tendered > 0 && (
							<div className="flex justify-between text-sm">
								<span>Change:</span>
								<span
									className={`font-bold ${changeDue > 0 ? "text-green-600" : ""}`}
								>
									${changeDue.toFixed(2)}
								</span>
							</div>
						)}
					</div>

					{/* Checkout button */}
					<Button
						className="w-full mt-4"
						size="lg"
						disabled={
							cart.length === 0 ||
							createMutation.isPending ||
							addItemMutation.isPending
						}
						onClick={handleSaleComplete}
					>
						{createMutation.isPending || addItemMutation.isPending ? (
							<Loader2 className="w-4 h-4 animate-spin mr-2" />
						) : (
							<Check className="w-4 h-4 mr-2" />
						)}
						Complete Sale — ${total.toFixed(2)}
					</Button>
				</CardContent>
			</Card>
		</div>
	);
}
