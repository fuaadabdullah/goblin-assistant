# AWS Private Inference Setup Plan

## Target architecture

Vercel customer UI -> Render API/control plane -> Tailscale SOCKS5 -> AWS EC2 private inference node.

The EC2 node runs llama.cpp first (`aws_vm`). A separate GPU/vLLM lane (`aws_vllm`) is added only after the basic path is proven.

## Guardrails

- Start in `us-east-1` to keep the path close to Render's Virginia region.
- Create an AWS Budget before any GPU instance.
- Use an EC2 IAM role and AWS Systems Manager Session Manager. Do not place long-lived AWS access keys on the instance.
- Require IMDSv2.
- Security group: no inbound internet rules for inference or control ports.
- Do not expose llama.cpp, vLLM, or the control agent on a public interface.
- Keep Oracle available as rollback until AWS passes end-to-end verification.

## Phase 1: Account and management plane

1. Enable MFA.
2. Verify current AWS Free Tier credits/eligibility.
3. Create a monthly budget alert.
4. Enable Systems Manager management for EC2.
5. Attach the minimum SSM instance role.
6. Require IMDSv2.

## Phase 2: First continuity node

Use Ubuntu 24.04 in `us-east-1`. Start with a small general-purpose instance for control-plane and Qwen3-0.6B continuity testing; do not treat it as the final high-throughput inference node.

Networking:
- Default or dedicated VPC is acceptable.
- Give the instance outbound internet access for bootstrap.
- No inbound application ports.
- Avoid an Elastic IP.
- A normal public IPv4 is the simplest initial bootstrap path but AWS bills public IPv4 addresses; later move to an IPv6/private-egress design if worthwhile.
- SSM is the management path. SSH remains closed by default.

Install:
- Tailscale
- llama.cpp
- Qwen3-0.6B continuity model
- read-only Goblin control agent
- systemd services

Tailscale hostname: `goblin-aws-001`.

Services bind only to the Tailscale IP:
- llama.cpp: `8081`
- read-only control agent: `18091`

## Phase 3: Authentication and Render cutover

Create a new inference bearer secret. Store it on EC2 with root-only permissions and as a Render secret. Never commit it.

Set Render:
- `LLAMACPP_AWS_ENDPOINT=http://<aws-tailnet-ip>:8081`
- `LLAMACPP_AWS_PROXY=socks5://localhost:1055`
- `LLAMACPP_AWS_API_KEY=<secret>`

Verify in order:
1. EC2 local `/health`.
2. `/v1/models` advertises `goblin-core`.
3. Control agent reports `read_only=true`.
4. Tailscale sees `goblin-render` and `goblin-aws-001` online.
5. Render `/api/v1/routing/health/aws_vm` returns healthy.
6. Send one real non-streaming `aws_vm` chat request.
7. Send one real streaming `aws_vm` request.
8. Verify latency/usage telemetry and zero provider-cost accounting.
9. Reboot EC2 and prove systemd recovery.
10. Stop/start EC2 and prove tailnet reconnection.

## Phase 4: GPU lane

Only after the continuity lane works, evaluate GPU EC2 pricing and availability in-region.

Current candidates:
- G6: NVIDIA L4, 24 GB on single-GPU sizes; good first target for inference.
- G6e: NVIDIA L40S, 48 GB per GPU when more VRAM/concurrency is needed.
- G7/G7e: newer Blackwell generation; use only if price/performance justifies it.

Do not launch a GPU before reviewing its current hourly price.

For the GPU lane:
1. Launch EC2 with the same SSM/Tailscale posture.
2. Install NVIDIA drivers/toolkit as required.
3. Run vLLM on the Tailscale IP only.
4. Configure `AWS_VLLM_ENDPOINT` and `AWS_VLLM_API_KEY`.
5. Verify models, chat, streaming, and any explicitly supported embedding/reranking endpoints.
6. Add the node to routing only after health and load tests pass.

## Phase 5: Cleanup

After AWS passes the complete path:
- Remove old GCP compute env vars and dashboards.
- Remove stale Oracle provider env values that are no longer needed.
- Keep Oracle only for the agreed rollback window, then stop/terminate it deliberately.
- Record the final recovery procedure.

## Definition of done

- No active `gcp_vm` or `gcp_vllm` provider IDs.
- `aws_vm` is the canonical private llama.cpp provider.
- `aws_vllm` is the canonical future GPU provider.
- Render contains no ML model runtime.
- AWS inference/control ports are tailnet-only.
- SSM works without public SSH.
- No static AWS credentials exist on EC2 or in Git.
- Provider health, non-streaming chat, streaming chat, restart recovery, and telemetry tests pass.
