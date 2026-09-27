# AWS Bedrock provider setup

Goblin Assistant exposes AWS as the `aws_bedrock` provider. Vertex AI and the existing Google integrations remain independent providers.

## Architecture

- API/control plane: Render
- Customer frontend: Vercel
- Managed AWS inference: Amazon Bedrock
- Self-hosted inference: Oracle / Node compute
- Default Bedrock model: `openai.gpt-oss-20b`
- Optional model: `qwen.qwen3-32b` (`aws-qwen3`)

The initial integration uses Bedrock Mantle's OpenAI-compatible Chat Completions API because it fits Goblin's current provider contract and exposes `/v1/models` for normal provider health checks. Native Bedrock Converse can be added later behind the same provider ID.

## Render secrets

Set in Render, never Git:

- `AWS_BEDROCK_API_KEY`
- `AWS_BEDROCK_BASE_URL=https://bedrock-mantle.us-east-1.api.aws/v1` (optional override)

Do not reuse `OPENAI_API_KEY` for Bedrock.

## Setup sequence

1. Start in `us-east-1`.
2. Open Amazon Bedrock and confirm the selected model is available.
3. Create a short-term Bedrock API key for initial validation.
4. Create an AWS Budget and billing alert before production traffic.
5. Put the Bedrock key in Render as `AWS_BEDROCK_API_KEY`.
6. Deploy and probe `/api/v1/routing/health/aws_bedrock`.
7. Run one bounded completion with `openai.gpt-oss-20b`.
8. Run one streaming completion.
9. Verify usage, latency, error classification, and cost telemetry.
10. Only then allow normal routing to select `aws_bedrock`.

For production, prefer short-lived/least-privilege credentials and keep model access limited to the models Goblin actually uses.
