import * as React from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?:
    "default" | "secondary" | "destructive" | "success" | "warning" | "outline";
}

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          {
            "border-transparent bg-primary text-primary-foreground shadow":
              variant === "default",
            "border-transparent bg-secondary text-secondary-foreground":
              variant === "secondary",
            "border-transparent bg-destructive text-destructive-foreground shadow":
              variant === "destructive",
            "border-transparent bg-[var(--color-success)] text-white shadow":
              variant === "success",
            "border-transparent bg-[var(--color-warning)] text-black shadow":
              variant === "warning",
            "text-foreground": variant === "outline",
          },
          className,
        )}
        {...props}
      />
    );
  },
);
Badge.displayName = "Badge";
