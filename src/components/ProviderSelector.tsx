interface Props {
	providers: string[];
	selected?: string;
	onChange?: (provider: string) => void;
}

export default function ProviderSelector({
	providers,
	selected,
	onChange,
}: Props) {
	if (!providers || providers.length === 0) return null;

	return (
		<div className="provider-selector" data-testid="provider-selector">
			<label htmlFor="provider-select" data-testid="provider-label">Provider:</label>
			<select
				id="provider-select"
				aria-label="Select provider"
				value={selected || providers[0]}
				onChange={(e) => onChange && onChange(e.currentTarget.value)}
				data-testid="provider-select"
			>
				{providers.map((p) => (
					<option key={p} value={p} data-testid={`provider-option-${p}`}>
						{p}
					</option>
				))}
			</select>
		</div>
	);
}
