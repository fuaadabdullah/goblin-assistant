---
title: "PASSKEY FRONTEND INTEGRATION"
description: "Passkey / WebAuthn — Frontend Integration Examples"
---

# Passkey / WebAuthn — Frontend Integration Examples

This file contains frontend integration examples for WebAuthn (passkey) flows.
The backend contains the canonical API endpoints; frontend usage examples live here so UI teams can implement them consistently.

## Registration Example (React / Browser)

```javascript
// 1. Request challenge
const { challenge } = await fetch('/auth/passkey/challenge', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: userEmail }),
}).then(r => r.json());

// 2. Get credentials from WebAuthn (registration)
const credential = await navigator.credentials.create({
  publicKey: {
    challenge: base64urlDecode(challenge),
    rp: { name: 'Goblin Assistant' },
    user: { id: new Uint8Array(16), name: userEmail, displayName: userName },
    pubKeyCredParams: [{ alg: -7, type: 'public-key' }],
    authenticatorSelection: { userVerification: 'preferred' },
  },
});

// 3. Send credential to backend for registration
await fetch('/auth/passkey/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: userEmail,
    credential_id: base64urlEncode(credential.rawId),
    public_key: base64urlEncode(credential.response.attestationObject),
  }),
});
```

## Authentication Example (React / Browser)

```javascript
// 1. Request challenge
const { challenge } = await fetch('/auth/passkey/challenge', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: userEmail }),
}).then(r => r.json());

// 2. Get signed assertion from authenticator
const assertion = await navigator.credentials.get({
  publicKey: {
    challenge: base64urlDecode(challenge),
    allowCredentials: [{ id: base64urlDecode(credentialId), type: 'public-key' }],
    userVerification: 'preferred',
  },
});

// 3. Send assertion to backend for verification (login)
const { access_token } = await fetch('/auth/passkey/auth', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: userEmail,
    credential_id: base64urlEncode(assertion.rawId),
    authenticator_data: base64urlEncode(assertion.response.authenticatorData),
    client_data_json: base64urlEncode(assertion.response.clientDataJSON),
    signature: base64urlEncode(assertion.response.signature),
  }),
}).then(r => r.json());

// 4. Store token or call client login handling function
console.log('Login token:', access_token);
```

## Notes

- Keep the challenge flow as single-use and short-lived (5 minutes) — the backend enforces this.
- Origin validation is required; ensure `FRONTEND_URL` in backend `.env` matches the production frontend domain.
- This example intentionally uses `base64urlEncode`/`base64urlDecode` utility functions — you can adapt utilities to your stack (e.g., `@noble/hashes` or `buffer` in Node).

For additional UI examples, see: `apps/goblin-assistant/docs/` and developer stories under `apps/goblin-assistant/src/stories/`.
