import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Pagination from "@/components/Pagination";

describe("Pagination", () => {
  it("renders page numbers and total", () => {
    render(
      <Pagination
        page={1}
        totalPages={4}
        total={100}
        hasPrev={false}
        hasNext={true}
        onPrev={() => {}}
        onNext={() => {}}
        onGoToPage={() => {}}
      />,
    );
    expect(screen.getByText("100 total")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("returns null when totalPages <= 1", () => {
    const { container } = render(
      <Pagination
        page={1}
        totalPages={1}
        total={10}
        hasPrev={false}
        hasNext={false}
        onPrev={() => {}}
        onNext={() => {}}
        onGoToPage={() => {}}
      />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("disables previous button when hasPrev is false", () => {
    render(
      <Pagination
        page={1}
        totalPages={4}
        total={100}
        hasPrev={false}
        hasNext={true}
        onPrev={() => {}}
        onNext={() => {}}
        onGoToPage={() => {}}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toBeDisabled();
  });

  it("disables next button when hasNext is false", () => {
    render(
      <Pagination
        page={4}
        totalPages={4}
        total={100}
        hasPrev={true}
        hasNext={false}
        onPrev={() => {}}
        onNext={() => {}}
        onGoToPage={() => {}}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons[buttons.length - 1]).toBeDisabled();
  });

  it("calls onNext when next button clicked", async () => {
    const user = userEvent.setup();
    let nextCalled = false;
    render(
      <Pagination
        page={1}
        totalPages={4}
        total={100}
        hasPrev={false}
        hasNext={true}
        onPrev={() => {}}
        onNext={() => {
          nextCalled = true;
        }}
        onGoToPage={() => {}}
      />,
    );
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[buttons.length - 1]);
    expect(nextCalled).toBe(true);
  });

  it("calls onPrev when previous button clicked", async () => {
    const user = userEvent.setup();
    let prevCalled = false;
    render(
      <Pagination
        page={2}
        totalPages={4}
        total={100}
        hasPrev={true}
        hasNext={true}
        onPrev={() => {
          prevCalled = true;
        }}
        onNext={() => {}}
        onGoToPage={() => {}}
      />,
    );
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[0]);
    expect(prevCalled).toBe(true);
  });

  it("calls onGoToPage with page number when clicked", async () => {
    const user = userEvent.setup();
    let gotoPage = 0;
    render(
      <Pagination
        page={1}
        totalPages={4}
        total={100}
        hasPrev={false}
        hasNext={true}
        onPrev={() => {}}
        onNext={() => {}}
        onGoToPage={(p) => {
          gotoPage = p;
        }}
      />,
    );
    const pageBtns = screen
      .getAllByRole("button")
      .filter((b) => !b.querySelector("svg"));
    await user.click(pageBtns[1]);
    expect(gotoPage).toBe(2);
  });

  it("renders ellipsis for large page ranges", () => {
    render(
      <Pagination
        page={5}
        totalPages={20}
        total={500}
        hasPrev={true}
        hasNext={true}
        onPrev={() => {}}
        onNext={() => {}}
        onGoToPage={() => {}}
      />,
    );
    const ellipses = screen.getAllByText("...");
    expect(ellipses.length).toBeGreaterThanOrEqual(1);
  });
});
