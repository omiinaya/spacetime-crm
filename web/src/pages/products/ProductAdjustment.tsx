import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Select } from '../../components/ui/select';
import { ClipboardList, ArrowRightLeft } from 'lucide-react';

interface Product {
  id: string;
  name: string;
  sku?: string;
  barcode?: string;
  description?: string;
  category?: string;
  price: number;
  cost: number;
  quantity_on_hand: number;
  quantity_committed: number;
  quantity_available: number;
  min_stock?: number;
  location?: string;
}

interface Adjustment {
  id: string;
  quantity_change: number;
  reason: string;
  reference_id?: string;
  notes?: string;
  created_at: number;
}

interface AdjForm {
  quantity_change: number;
  reason: string;
  reference_id: string;
  notes: string;
}

interface TransferForm {
  destProductId: string;
  quantity: number;
  notes: string;
}

const reasonColors: Record<string, string> = {
  received: 'text-green-400',
  sold: 'text-red-400',
  damaged: 'text-orange-400',
  returned: 'text-blue-400',
  counted: 'text-purple-400',
  transferred: 'text-cyan-400',
};

interface ProductAdjustmentProps {
  selectedProduct: Product | null;
  adjForm: AdjForm;
  setAdjForm: (f: AdjForm) => void;
  adjustStock: () => void;
  transferForm: TransferForm;
  setTransferForm: (f: TransferForm) => void;
  transferSearch: string;
  setTransferSearch: (v: string) => void;
  transferProducts: any;
  transferMutation: any;
  adjustments: Adjustment[];
  fmtDate: (ts: number) => string;
  setSelectedProduct: any;
  printBarcodeLabel: (barcode: string, name: string, price: number, sku: string) => void;
}

export default function ProductAdjustment({
  selectedProduct,
  adjForm,
  setAdjForm,
  adjustStock,
  transferForm,
  setTransferForm,
  transferSearch,
  setTransferSearch,
  transferProducts,
  transferMutation,
  adjustments,
  fmtDate,
  setSelectedProduct,
  printBarcodeLabel,
}: ProductAdjustmentProps) {
  if (!selectedProduct) return null;

  return (
    <div className="space-y-4">
      {/* Back button (mobile) */}
      <button
        onClick={() => setSelectedProduct(null)}
        className="lg:hidden text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
      >
        ← Back to list
      </button>

      {/* Product detail card */}
      <Card>
        <CardHeader>
          <CardTitle>{selectedProduct.name}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold">{selectedProduct.quantity_on_hand}</p>
              <p className="text-xs text-muted-foreground">On Hand</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{selectedProduct.quantity_committed}</p>
              <p className="text-xs text-muted-foreground">Committed</p>
            </div>
            <div>
              <p
                className={`text-2xl font-bold ${(selectedProduct.quantity_available ?? 0) <= 0 ? 'text-destructive' : ''}`}
              >
                {selectedProduct.quantity_available}
              </p>
              <p className="text-xs text-muted-foreground">Available</p>
            </div>
          </div>
          {selectedProduct.min_stock && selectedProduct.min_stock > 0 && (
            <div className="flex items-center justify-between text-sm px-2 py-1.5 rounded bg-muted/50">
              <span>Min Stock:</span>
              <span
                className={`font-medium ${selectedProduct.quantity_on_hand <= selectedProduct.min_stock ? 'text-destructive' : 'text-green-400'}`}
              >
                {selectedProduct.min_stock}
              </span>
            </div>
          )}
          <p className="text-sm">
            Price: <span className="font-medium">${selectedProduct.price.toFixed(2)}</span> &middot;
            Cost: <span className="font-medium">${selectedProduct.cost.toFixed(2)}</span>
          </p>
          {selectedProduct.barcode && (
            <p className="text-sm">
              Barcode:{' '}
              <span className="font-mono text-xs text-muted-foreground">
                {selectedProduct.barcode}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="ml-1 inline-flex h-5 w-5 align-middle"
                onClick={() =>
                  printBarcodeLabel(
                    selectedProduct.barcode!,
                    selectedProduct.name,
                    selectedProduct.price,
                    selectedProduct.sku || '',
                  )
                }
                title="Print barcode label"
              >
                <span className="h-3 w-3">🖨</span>
              </Button>
            </p>
          )}
          {selectedProduct.description && (
            <p className="text-sm text-muted-foreground">{selectedProduct.description}</p>
          )}
        </CardContent>
      </Card>

      {/* Stock adjustment */}
      <Card>
        <CardHeader>
          <CardTitle>
            <ClipboardList className="h-4 w-4 inline mr-1.5" />
            Adjust Stock
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <Input
              type="number"
              placeholder="Quantity change"
              value={adjForm.quantity_change}
              onChange={(e) =>
                setAdjForm({
                  ...adjForm,
                  quantity_change: parseFloat(e.target.value) || 0,
                })
              }
            />
            <Select
              value={adjForm.reason}
              onChange={(e) => setAdjForm({ ...adjForm, reason: e.target.value })}
            >
              <option value="received">Received</option>
              <option value="sold">Sold</option>
              <option value="damaged">Damaged</option>
              <option value="returned">Returned</option>
              <option value="counted">Counted</option>
              <option value="transferred">Transferred</option>
            </Select>
          </div>
          <Input
            placeholder="Reference (e.g. PO-1234)"
            value={adjForm.reference_id}
            onChange={(e) => setAdjForm({ ...adjForm, reference_id: e.target.value })}
          />
          <Input
            placeholder="Notes"
            value={adjForm.notes}
            onChange={(e) => setAdjForm({ ...adjForm, notes: e.target.value })}
          />
          <Button onClick={adjustStock}>Apply Adjustment</Button>
        </CardContent>
      </Card>

      {/* Stock transfer */}
      <Card>
        <CardHeader>
          <CardTitle>
            <ArrowRightLeft className="h-4 w-4 inline mr-1.5" />
            Transfer Stock
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Move stock from <strong>{selectedProduct.name}</strong> to another product
          </p>
          <div>
            <Input
              placeholder="Search destination product..."
              value={transferSearch}
              onChange={(e) => setTransferSearch(e.target.value)}
            />
            {transferSearch.length >= 1 && (
              <div className="mt-1 max-h-32 overflow-y-auto border border-border rounded-md bg-card">
                {(transferProducts?.products ?? [])
                  .filter((p: { id: string }) => p.id !== selectedProduct.id)
                  .map((p: { id: string; name: string; quantity_on_hand: number }) => (
                    <button
                      key={p.id}
                      className={`w-full text-left px-3 py-1.5 text-sm hover:bg-muted/50 transition-colors ${transferForm.destProductId === p.id ? 'bg-primary/10 font-medium' : ''}`}
                      onClick={() => {
                        setTransferForm({
                          ...transferForm,
                          destProductId: p.id,
                        });
                        setTransferSearch(p.name);
                      }}
                    >
                      {p.name}{' '}
                      <span className="text-xs text-muted-foreground">
                        ({p.quantity_on_hand} in stock)
                      </span>
                    </button>
                  ))}
                {(transferProducts?.products ?? []).filter(
                  (p: { id: string }) => p.id !== selectedProduct.id,
                ).length === 0 && (
                  <p className="px-3 py-1.5 text-xs text-muted-foreground">No matching products</p>
                )}
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-muted-foreground block mb-1">Quantity</label>
              <Input
                type="number"
                min={1}
                value={transferForm.quantity}
                onChange={(e) =>
                  setTransferForm({
                    ...transferForm,
                    quantity: Math.max(1, parseInt(e.target.value) || 1),
                  })
                }
              />
            </div>
            <div className="flex items-end">
              <span className="text-xs text-muted-foreground pb-2">
                Max: {selectedProduct.quantity_on_hand}
              </span>
            </div>
          </div>
          <Input
            placeholder="Transfer notes (optional)"
            value={transferForm.notes}
            onChange={(e) => setTransferForm({ ...transferForm, notes: e.target.value })}
          />
          <Button
            onClick={() => transferMutation.mutate()}
            disabled={!transferForm.destProductId || transferMutation.isPending}
          >
            {transferMutation.isPending ? 'Transferring...' : 'Transfer'}
          </Button>
        </CardContent>
      </Card>

      {/* History */}
      <Card>
        <CardHeader>
          <CardTitle>Adjustment History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {adjustments.length === 0 && (
              <p className="text-sm text-muted-foreground">No adjustments yet</p>
            )}
            {adjustments
              .slice()
              .reverse()
              .map((a) => (
                <div
                  key={a.id}
                  className="flex items-center justify-between text-sm p-2 rounded bg-muted/50"
                >
                  <div className="min-w-0 flex-1">
                    <span
                      className={`font-medium ${a.quantity_change > 0 ? 'text-green-400' : 'text-red-400'}`}
                    >
                      {a.quantity_change > 0 ? '+' : ''}
                      {a.quantity_change}
                    </span>
                    <span className={`ml-2 text-xs ${reasonColors[a.reason] || ''}`}>
                      {a.reason}
                    </span>
                    {a.reference_id && (
                      <span className="ml-2 text-xs text-muted-foreground">{a.reference_id}</span>
                    )}
                    <p className="text-xs text-muted-foreground mt-0.5">{a.notes}</p>
                  </div>
                  <span className="text-xs text-muted-foreground ml-2 shrink-0">
                    {fmtDate(a.created_at)}
                  </span>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
