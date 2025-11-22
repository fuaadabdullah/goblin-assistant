import type { CostSummary } from "../api/tauri-client";

interface Props {
	costSummary?: CostSummary | null;
}

export default function CostPanel({ costSummary }: Props) {
	if (!costSummary) return null;

	return (
		<div className="cost-panel">
			<h3>Cost Summary</h3>
			<div>
				<strong>Total:</strong> ${costSummary.total_cost.toFixed(6)}
			</div>
			<div>
				<strong>By Provider:</strong>
				<ul>
					{Object.entries(costSummary.cost_by_provider).map(([p, c]) => (
						<li key={p}>
							{p}: ${c.toFixed(6)}
						</li>
					))}
				</ul>
			</div>
			<div>
				<strong>By Model:</strong>
				<ul>
					{Object.entries(costSummary.cost_by_model).map(([m, c], i) => (
						<li key={`${m}-${i}`}>
							{m}: ${c.toFixed(6)}
						</li>
					))}
				</ul>
			</div>
		</div>
	);
}
