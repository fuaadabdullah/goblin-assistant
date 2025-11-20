import { describe, it, expect } from "vitest";
import { greet } from "../src/lib/greet";

describe("greet", () => {
  it("returns greeting message", () => {
    expect(greet("Tester")).toBe("Hello from Goblin Assistant, Tester!");
  });
});
