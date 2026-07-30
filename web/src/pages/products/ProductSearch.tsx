import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Search, Scan, AlertTriangle } from 'lucide-react';

interface ProductSearchProps {
  search: string;
  handleSearch: (val: string) => void;
  categoryFilter: string;
  setCategoryFilter: (val: string) => void;
  categories: string[] | undefined;
  barcodeLookup: string;
  setBarcodeLookup: (val: string) => void;
  handleBarcodeLookup: (e: React.KeyboardEvent) => void;
  lowStockCount: number;
  notifyLowStockMutation: { isPending: boolean; mutate: () => void };
}

export default function ProductSearch({
  search,
  handleSearch,
  categoryFilter,
  setCategoryFilter,
  categories,
  barcodeLookup,
  setBarcodeLookup,
  handleBarcodeLookup,
  lowStockCount,
  notifyLowStockMutation,
}: ProductSearchProps) {
  return (
    <>
      {/* Search + category filter */}
      <div className="flex gap-2 items-center flex-wrap">
        <Input
          placeholder="Search products..."
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="max-w-full sm:max-w-sm"
        />
        <select
          value={categoryFilter}
          onChange={(e) => {
            setCategoryFilter(e.target.value);
          }}
          className="h-9 rounded-md border border-input bg-background px-3 text-xs outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All categories</option>
          {categories?.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <div className="flex items-center gap-1 border rounded-md px-2 py-1 bg-muted/30 max-w-full sm:max-w-[200px] flex-1 sm:flex-none">
          <Scan className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <input
            type="text"
            placeholder="Scan barcode..."
            value={barcodeLookup}
            onChange={(e) => setBarcodeLookup(e.target.value)}
            onKeyDown={handleBarcodeLookup}
            className="bg-transparent border-none outline-none text-xs w-full py-0.5"
          />
        </div>
      </div>

      {lowStockCount > 0 && (
        <div className="flex items-center justify-between rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-400" />
            <p className="text-sm text-amber-300">
              <span className="font-semibold">{lowStockCount}</span> product
              {lowStockCount !== 1 ? 's' : ''} below minimum stock
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="border-amber-500/40 text-amber-300 hover:bg-amber-500/20"
              onClick={() =>
                document.getElementById('low-stock-list')?.scrollIntoView({ behavior: 'smooth' })
              }
            >
              View
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="border-amber-500/40 text-amber-300 hover:bg-amber-500/20"
              onClick={() => notifyLowStockMutation.mutate()}
              disabled={notifyLowStockMutation.isPending}
            >
              {notifyLowStockMutation.isPending ? 'Sending...' : 'Notify Admin'}
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
