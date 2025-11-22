import type { OrchestrationPlan, OrchestrationStep } from "../api/tauri-client";

interface Props {
	plan: OrchestrationPlan;
}

export default function OrchestrationPreview({ plan }: Props) {
	if (!plan) return null;

	const batches: Record<number, OrchestrationStep[]> = {};
	plan.steps.forEach((step) => {
		batches[step.batch] = batches[step.batch] || [];
		batches[step.batch].push(step);
	});

	return (
		<div className="orchestration-preview">
			<h3>Orchestration Preview</h3>
			<div className="batches">
				{Object.keys(batches)
					.sort((a, b) => Number(a) - Number(b))
					.map((batchKey) => (
						<div key={batchKey} className="batch">
							<strong>Batch {batchKey}</strong>
							<ul>
								{batches[Number(batchKey)].map((s) => (
									<li key={s.id}>
										<code>{s.id}</code>: {s.task} <em>({s.goblin})</em>
									</li>
								))}
							</ul>
						</div>
					))}
			</div>
			<div className="plan-meta">
				<small>
					Batches: {plan.total_batches}, max parallel: {plan.max_parallel}
				</small>
			</div>
		</div>
	);
}
