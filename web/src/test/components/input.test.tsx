import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Input } from "@/components/ui/input";

describe("Input", () => {
  it("renders with default classes", () => {
    render(<Input placeholder="Enter name" />);
    const input = screen.getByPlaceholderText("Enter name");
    expect(input).toHaveClass("flex h-9 w-full rounded-md border");
  });

  it("accepts additional className", () => {
    render(<Input className="custom-input" placeholder="test" />);
    expect(screen.getByPlaceholderText("test")).toHaveClass("custom-input");
  });

  it("accepts value and onChange", async () => {
    const user = userEvent.setup();
    let value = "";
    render(<Input placeholder="type here" onChange={(e) => { value = e.target.value; }} />);
    const input = screen.getByPlaceholderText("type here");
    await user.type(input, "hello");
    expect(value).toBe("hello");
  });

  it("can be disabled", () => {
    render(<Input disabled placeholder="disabled" />);
    expect(screen.getByPlaceholderText("disabled")).toBeDisabled();
  });

  it("forwards ref", () => {
    const ref = { current: null as any };
    render(<Input ref={ref} placeholder="ref" />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
  });
});
