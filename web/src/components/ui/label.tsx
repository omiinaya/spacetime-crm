import { cn } from "../../lib/utils";

export function Label({ children, className, htmlFor, ...props }: { children: React.ReactNode; className?: string; htmlFor?: string; [key: string]: any }) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn("text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70", className)}
      {...props}
    >
      {children}
    </label>
  );
}
