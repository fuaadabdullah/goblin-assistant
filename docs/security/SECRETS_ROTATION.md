# Secrets Rotation & Remediation

This document tracks leaked/embedded secrets discovered in the repository and the remediation steps taken.

Discovered secrets (examples) and actions taken:

- sandbox_demo.py
  - Issue: Embedded `API_KEY` value committed in repository.
  - Action: Replaced with environment variable usage (`API_AUTH_KEY` / `SANDBOX_API_KEY`).

- test_production_comprehensive.py
  - Issue: Embedded `API_KEY` value committed in repository.
  - Action: Replaced with environment variable usage (`API_AUTH_KEY`).

- PROVIDER_STATUS_REPORT.md
  - Issue: Example cURL contained an actual bearer token.
  - Action: Replaced visible token with `[REDACTED_API_KEY]` placeholder.

- KAMATERA_CHAT_STATUS.md
  - Issue: `.env.local` example contained a real `LOCAL_LLM_API_KEY`.
  - Action: Replaced with `[REDACTED_LOCAL_LLM_API_KEY]` placeholder.

Recommended immediate steps (you must perform):

1. Rotate/Revoke exposed keys immediately:
   - Render API key that was previously committed in `restore_gcp_creds.py`.
   - Any API tokens found in `sandbox_demo.py`, `test_production_comprehensive.py`, and other files (if still active).

2. Verify no other active keys exist in the repository history (use `git log --all -S '<key-fragment>'` or use a secrets scanner).

3. After rotating keys, update your hosting providers (Render, Vercel, Supabase, etc.) with new secrets through their dashboards.

4. Consider enabling automated secret scanning in CI (GitHub secret scanning or tools like truffleHog, ghzsecrets-scanner).

5. Do not re-commit or paste credentials into the repository. Use `.env.local` for local development (exclude from git) and provider dashboards for production secrets.

Notes:
- This patch removes visible secrets from the working tree, but history still contains them. If you need to purge secrets from git history, follow the provider guidance (rotate keys first), then use `git filter-branch`/`git filter-repo` or GitHub's secret removal instructions.

Contact and verification:
- After you rotate keys, I can help update remote secrets (Render/Vercel) using secure workflows (not by committing secrets into this repo).
