import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";

describe("Badge", () => {
	it("renders with default (primary) variant", () => {
		render(<Badge>Active</Badge>);
		const badge = screen.getByText("Active");
		expect(badge).toHaveClass("bg-primary text-primary-foreground");
	});

	it("renders with secondary variant", () => {
		render(<Badge variant="secondary">Draft</Badge>);
		expect(screen.getByText("Draft")).toHaveClass(
			"bg-secondary text-secondary-foreground",
		);
	});

	it("renders with destructive variant", () => {
		render(<Badge variant="destructive">Deleted</Badge>);
		expect(screen.getByText("Deleted")).toHaveClass(
			"bg-destructive text-destructive-foreground",
		);
	});

	it("renders with outline variant", () => {
		render(<Badge variant="outline">Outline</Badge>);
		expect(screen.getByText("Outline")).toHaveClass("text-foreground");
	});

	it("accepts additional className", () => {
		render(<Badge className="custom-badge">Custom</Badge>);
		expect(screen.getByText("Custom")).toHaveClass("custom-badge");
	});
});
