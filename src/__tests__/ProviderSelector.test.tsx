import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ProviderSelector from "../components/ProviderSelector";

describe("ProviderSelector", () => {
	it("renders nothing when no providers are provided", () => {
		const { container } = render(<ProviderSelector providers={[]} />);
		expect(container.firstChild).toBeNull();
	});

	it("renders nothing when providers is undefined", () => {
		const { container } = render(<ProviderSelector providers={undefined as any} />);
		expect(container.firstChild).toBeNull();
	});

	it("renders select with providers", () => {
		const providers = ["openai", "anthropic", "google"];
		render(<ProviderSelector providers={providers} />);

		expect(screen.getByTestId("provider-selector")).toBeInTheDocument();
		expect(screen.getByTestId("provider-label")).toHaveTextContent("Provider:");
		expect(screen.getByTestId("provider-select")).toBeInTheDocument();

		// Check all provider options are rendered
		expect(screen.getByTestId("provider-option-openai")).toBeInTheDocument();
		expect(screen.getByTestId("provider-option-anthropic")).toBeInTheDocument();
		expect(screen.getByTestId("provider-option-google")).toBeInTheDocument();
	});

	it("selects first provider by default when no selected prop provided", () => {
		const providers = ["openai", "anthropic"];
		render(<ProviderSelector providers={providers} />);

		const select = screen.getByTestId("provider-select");
		expect(select).toHaveValue("openai");
	});

	it("selects specified provider when selected prop is provided", () => {
		const providers = ["openai", "anthropic", "google"];
		render(<ProviderSelector providers={providers} selected="anthropic" />);

		const select = screen.getByTestId("provider-select");
		expect(select).toHaveValue("anthropic");
	});

	it("calls onChange when provider is selected", () => {
		const providers = ["openai", "anthropic"];
		const onChange = vi.fn();
		render(<ProviderSelector providers={providers} onChange={onChange} />);

		const select = screen.getByTestId("provider-select");
		fireEvent.change(select, { target: { value: "anthropic" } });

		expect(onChange).toHaveBeenCalledWith("anthropic");
		expect(onChange).toHaveBeenCalledTimes(1);
	});

	it("does not call onChange when onChange prop is not provided", () => {
		const providers = ["openai", "anthropic"];
		render(<ProviderSelector providers={providers} />);

		const select = screen.getByTestId("provider-select");

		// Initially should have the first provider selected
		expect(select).toHaveValue("openai");

		// Try to change the selection
		fireEvent.change(select, { target: { value: "anthropic" } });

		// Since it's a controlled component without onChange, the value should remain the same
		expect(select).toHaveValue("openai");
	});

	it("updates selected value when selected prop changes", () => {
		const providers = ["openai", "anthropic"];
		const { rerender } = render(<ProviderSelector providers={providers} selected="openai" />);

		expect(screen.getByTestId("provider-select")).toHaveValue("openai");

		rerender(<ProviderSelector providers={providers} selected="anthropic" />);
		expect(screen.getByTestId("provider-select")).toHaveValue("anthropic");
	});

	it("handles single provider correctly", () => {
		const providers = ["openai"];
		render(<ProviderSelector providers={providers} />);

		expect(screen.getByTestId("provider-selector")).toBeInTheDocument();
		expect(screen.getByTestId("provider-select")).toHaveValue("openai");
		expect(screen.getByTestId("provider-option-openai")).toBeInTheDocument();
	});

	it("maintains accessibility attributes", () => {
		const providers = ["openai", "anthropic"];
		render(<ProviderSelector providers={providers} />);

		const select = screen.getByTestId("provider-select");
		expect(select).toHaveAttribute("id", "provider-select");
		expect(select).toHaveAttribute("aria-label", "Select provider");

		const label = screen.getByTestId("provider-label");
		expect(label).toHaveAttribute("for", "provider-select");
	});

	it("sanitizes provider names for data-testid attributes", () => {
		const providers = ["openai", "anthropic-provider", "google_cloud"];
		render(<ProviderSelector providers={providers} />);

		expect(screen.getByTestId("provider-option-openai")).toBeInTheDocument();
		expect(screen.getByTestId("provider-option-anthropic-provider")).toBeInTheDocument();
		expect(screen.getByTestId("provider-option-google_cloud")).toBeInTheDocument();
	});

	it("handles provider names with special characters", () => {
		const providers = ["openai/gpt-4", "anthropic.claude", "google@vertex"];
		render(<ProviderSelector providers={providers} />);

		expect(screen.getByTestId("provider-option-openai/gpt-4")).toBeInTheDocument();
		expect(screen.getByTestId("provider-option-anthropic.claude")).toBeInTheDocument();
		expect(screen.getByTestId("provider-option-google@vertex")).toBeInTheDocument();
	});
});
