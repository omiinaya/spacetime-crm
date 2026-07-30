import { Receipt, ShoppingCart, Lock, Loader2 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Card, CardContent } from '../../components/ui/card';
import { POSCounterSale } from '../../lib/api';

interface HistoryViewProps {
  salesHistory: POSCounterSale[] | undefined;
  loadingHistory: boolean;
  setMode: (mode: 'sale' | 'history' | 'receipt') => void;
  onViewReceipt: (saleId: string) => void;
  setLocked: (locked: boolean) => void;
}

export default function HistoryView({
  salesHistory,
  loadingHistory,
  setMode,
  onViewReceipt,
  setLocked,
}: HistoryViewProps) {
  return (
    <div className="p-4 max-w-4xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <Receipt className="w-5 h-5" /> Sale History
        </h2>
        <Button variant="outline" size="sm" onClick={() => setMode('sale')}>
          <ShoppingCart className="w-4 h-4 mr-1" /> New Sale
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setLocked(true)} title="Lock POS terminal">
          <Lock className="w-4 h-4" />
        </Button>
      </div>

      {loadingHistory ? (
        <div className="flex justify-center py-10">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
      ) : (
        <div className="grid gap-3">
          {salesHistory?.map((sale: POSCounterSale) => (
            <Card
              key={sale.id}
              className="hover:bg-accent/50 cursor-pointer"
              onClick={() => onViewReceipt(sale.id)}
            >
              <CardContent className="p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium flex items-center gap-2">
                    Receipt #{sale.receipt_number}
                    {sale.status === 'refunded' && (
                      <Badge variant="destructive" className="text-xs">
                        Refunded
                      </Badge>
                    )}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {sale.customer_name} &middot; {new Date(sale.created_at).toLocaleDateString()}
                  </p>
                  <p className="text-xs text-muted-foreground">{sale.items_count} item(s)</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold">${sale.total.toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground capitalize">{sale.payment_method}</p>
                </div>
              </CardContent>
            </Card>
          ))}
          {(!salesHistory || salesHistory.length === 0) && (
            <p className="text-center text-muted-foreground py-10">No sales yet</p>
          )}
        </div>
      )}
    </div>
  );
}
