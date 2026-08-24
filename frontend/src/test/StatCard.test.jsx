import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatCard from "../components/StatCard";

describe("StatCard", () => {
  it("renders the label and value", () => {
    render(<StatCard label="Sites Scored" value="128" delta="+12 this week" />);
    expect(screen.getByText("Sites Scored")).toBeTruthy();
    expect(screen.getByText("128")).toBeTruthy();
  });
});
