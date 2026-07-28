# Secret Exposure Incident Response Runbook

Use this runbook when credentials, keys, or other sensitive material are suspected in repository content.

## 1. Detect and Triage

1. Confirm the finding source (CI secret scan, manual report, provider alert).
2. Identify affected material:
   - Secret type (API key, service account JSON, private key, password).
   - File path and commit references.
   - Any known downstream systems using the secret.
3. Open an incident ticket and record timeline, owner, and scope.

## 2. Contain Immediately

1. Remove exposed material from current branch by replacing with placeholders.
2. Block further propagation:
   - Pause or restrict deployments using the impacted secret.
   - Disable compromised automation jobs if they leak logs with secret values.
3. Keep all remediation actions in audited channels.

## 3. Revoke and Rotate

1. Revoke compromised credentials at the provider first.
2. Create replacement credentials with least privilege.
3. Update runtime secret stores (Render/Vercel/GitHub Secrets/Bitwarden/etc.).
4. Verify old credentials are unusable.

## 4. Purge and Verify Repository State

1. Ensure the working tree no longer contains secret material.
2. Run `python scripts/security/scan_secrets.py` and resolve findings.
3. If secrets exist in git history and policy requires cleanup:
   - Rotate/revoke first.
   - Purge history with approved tooling/process.
   - Force-push only under change-control approval.
4. Confirm CI secret scan is green on the remediation branch.

## 5. Validate Downstream Impact

1. Verify applications and integrations work with new credentials.
2. Validate authentication failures for revoked credentials.
3. Monitor logs/alerts for replay or repeated access attempts.

## 6. Post-Incident Hardening

1. Add missing detection patterns to `scripts/security/scan_secrets.py`.
2. Add precise false-positive patterns to `.secret-scan-allowlist.txt` only when justified.
3. Document root cause and preventive actions in the incident review.

## Notes

- Never commit real secrets to example files, env templates, or docs, even if encoded.
- Treat base64-encoded key material as sensitive plaintext.
