import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
	Card,
	CardHeader,
	CardTitle,
	CardDescription,
	CardContent,
	CardFooter,
} from "@/components/ui/card";

describe("Card", () => {
	it("renders with default classes", () => {
		render(<Card>Card content</Card>);
		const card = screen.getByText("Card content");
		expect(card).toHaveClass("rounded-lg border border-border");
	});

	it("accepts additional className", () => {
		render(<Card className="custom-card">Custom</Card>);
		expect(screen.getByText("Custom")).toHaveClass("custom-card");
	});
});

describe("CardHeader", () => {
	it("renders with flex layout", () => {
		render(<CardHeader>Header</CardHeader>);
		expect(screen.getByText("Header")).toHaveClass(
			"flex flex-col space-y-1.5 p-4",
		);
	});
});

describe("CardTitle", () => {
	it("renders as h3 with correct classes", () => {
		render(<CardTitle>Title</CardTitle>);
		const title = screen.getByRole("heading", { name: /title/i });
		expect(title).toHaveClass("font-semibold leading-none tracking-tight");
	});
});

describe("CardDescription", () => {
	it("renders with muted text", () => {
		render(<CardDescription>Description text</CardDescription>);
		const desc = screen.getByText("Description text");
		expect(desc).toHaveClass("text-sm text-muted-foreground");
	});
});

describe("CardContent", () => {
	it("renders with padding", () => {
		render(<CardContent>Content</CardContent>);
		expect(screen.getByText("Content")).toHaveClass("p-4 pt-0");
	});
});

describe("CardFooter", () => {
	it("renders with flex and padding", () => {
		render(<CardFooter>Footer</CardFooter>);
		expect(screen.getByText("Footer")).toHaveClass(
			"flex items-center p-4 pt-0",
		);
	});
});
