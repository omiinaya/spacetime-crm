import { cn } from "../../lib/utils";

export interface TabDef {
	id: string;
	label: string;
}

interface TabsProps {
	tabs: TabDef[];
	active: string;
	onChange: (id: string) => void;
	className?: string;
}

/**
 * Lightweight segmented tab bar used for page-level sub-navigation
 * (e.g. Settings sections, Payments → Payment Methods → Gift Cards).
 */
export function Tabs({ tabs, active, onChange, className }: TabsProps) {
	return (
		<div
			role="tablist"
			className={cn(
				"flex flex-wrap gap-1 border-b border-border pb-0",
				className,
			)}
		>
			{tabs.map((tab) => (
				<button
					key={tab.id}
					role="tab"
					aria-selected={active === tab.id}
					onClick={() => onChange(tab.id)}
					className={cn(
						"flex items-center gap-2 px-4 py-2 text-sm rounded-t-md transition-colors border-b-2",
						active === tab.id
							? "border-primary text-foreground font-medium"
							: "border-transparent text-muted-foreground hover:text-foreground",
					)}
				>
					{tab.label}
				</button>
			))}
		</div>
	);
}
