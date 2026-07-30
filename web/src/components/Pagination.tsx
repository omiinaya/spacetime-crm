import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./ui/button";

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  onGoToPage: (page: number) => void;
}

export default function Pagination({
  page,
  totalPages,
  total,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
  onGoToPage,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  // Generate visible page numbers
  const getPageNumbers = (): (number | "...")[] => {
    const pages: (number | "...")[] = [];
    const delta = 2;
    const start = Math.max(1, page - delta);
    const end = Math.min(totalPages, page + delta);

    if (start > 1) {
      pages.push(1);
      if (start > 2) pages.push("...");
    }
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    if (end < totalPages) {
      if (end < totalPages - 1) pages.push("...");
      pages.push(totalPages);
    }
    return pages;
  };

  return (
    <div className="flex items-center justify-between pt-4 pb-2">
      <div className="text-sm text-muted-foreground">{total} total</div>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon"
          disabled={!hasPrev}
          onClick={onPrev}
          className="h-8 w-8"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        {getPageNumbers().map((p, i) =>
          p === "..." ? (
            <span key={`e${i}`} className="px-1 text-muted-foreground text-sm">
              ...
            </span>
          ) : (
            <Button
              key={p}
              variant={p === page ? "default" : "outline"}
              size="icon"
              onClick={() => onGoToPage(p)}
              className="h-8 w-8 text-sm"
            >
              {p}
            </Button>
          ),
        )}
        <Button
          variant="outline"
          size="icon"
          disabled={!hasNext}
          onClick={onNext}
          className="h-8 w-8"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
