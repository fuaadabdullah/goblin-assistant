---
title: "SECURITY"
description: "🔒 Security Implementation Guide"
---

# 🔒 Security Implementation Guide

## Content Security Policy (CSP)

The Goblin Assistant implements a comprehensive Content Security Policy to protect against XSS attacks and other code injection vulnerabilities.

### Development Configuration

During development, CSP headers are automatically set by Vite in `vite.config.ts`:

```typescript
headers: {
  'Content-Security-Policy': [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self' https://goblin-backend.fly.dev https://challenges.cloudflare.com ws://localhost:3000",
    "frame-src https://challenges.cloudflare.com",
    "base-uri 'self'",
    "form-action 'self'"
  ].join('; '),
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
}
```

### Production Deployment

For production deployments, **CSP must be set via server headers** (not meta tags) for maximum security:

#### Backend Implementation (Recommended)

```typescript

// Express.js example
app.use((req, res, next) => {
  // Content Security Policy
  res.setHeader('Content-Security-Policy',
    "default-src 'self'; " +
    "script-src 'self' <https://challenges.cloudflare.com;> " +
    "style-src 'self' 'unsafe-inline'; " +
    "connect-src 'self' <https://goblin-backend.fly.dev> <https://goblin-assistant-backend.onrender.com;">
  );

  // Additional Security Headers
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');

  next();
});
```

#### Fly.io Deployment

For Fly.io deployments, add security headers in `fly.toml`:

```toml
[http_service]
  [http_service.headers]
    Content-Security-Policy = "default-src 'self'; script-src 'self' https://challenges.cloudflare.com; style-src 'self' 'unsafe-inline'; connect-src 'self' https://goblin-backend.fly.dev https://goblin-assistant-backend.onrender.com;"
    X-Content-Type-Options = "nosniff"
    X-Frame-Options = "DENY"
    Strict-Transport-Security = "max-age=31536000; includeSubDomains"
    Referrer-Policy = "strict-origin-when-cross-origin"
```

#### Vercel Deployment

For Vercel deployments, add headers in `vercel.json`:

```json

{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self' <https://challenges.cloudflare.com;> style-src 'self' 'unsafe-inline'; connect-src 'self' <https://goblin-backend.fly.dev> <https://goblin-assistant-backend.onrender.com;">
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "Strict-Transport-Security",
          "value": "max-age=31536000; includeSubDomains"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        }
      ]
    }
  ]
}
```

### CSP Policy Explanation

- **`default-src 'self'`**: Only allow resources from the same origin
- **`script-src 'self' <https://challenges.cloudflare.com`**:> Allow scripts from self and Cloudflare Turnstile
- **`style-src 'self' 'unsafe-inline'`**: Allow styles from self and inline styles (required for some UI libraries)
- **`connect-src 'self' <https://goblin-backend.fly.dev`**:> Allow API connections to backend
- **`frame-src <https://challenges.cloudflare.com`**:> Allow Turnstile widget iframe
- **`img-src 'self' data: https:`**: Allow images from self, data URIs, and HTTPS sources
- **`font-src 'self' data:`**: Allow fonts from self and data URIs
- **`base-uri 'self'`**: Restrict base URI to same origin
- **`form-action 'self'`**: Only allow form submissions to same origin

### Additional Security Headers

- **`X-Content-Type-Options: nosniff`**: Prevents MIME type sniffing
- **`X-Frame-Options: DENY`**: Prevents clickjacking attacks
- **`Strict-Transport-Security`**: Forces HTTPS connections
- **`Referrer-Policy`**: Controls referrer information sent with requests

### Testing CSP

1. **Development**: CSP headers are automatically applied by Vite
2. **Production**: Verify headers are set by the server:

   ```bash
   curl -I https://your-domain.com
   ```

3. **Browser DevTools**: Check Console for CSP violations
4. **CSP Evaluator**: Use Google's CSP Evaluator tool

### Troubleshooting

**Common CSP Issues:**

1. **Inline scripts/styles blocked**: Add `'unsafe-inline'` to `script-src`/`style-src` if necessary
2. **External resources blocked**: Add specific domains to appropriate directives
3. **WebSocket connections blocked**: Add `ws://` or `wss://` to `connect-src`
4. **Font loading issues**: Add font domains to `font-src`

**Debugging:**

- Use browser DevTools Network tab to inspect response headers
- Check browser Console for CSP violation reports
- Temporarily relax CSP during development to identify blocked resources

### Security Monitoring

Monitor for CSP violations using:

- Browser console reports
- Server logs for blocked requests
- Security monitoring tools (Sentry)

Regularly review and update CSP based on:

- New features requiring additional resources
- Security audit findings
- Third-party service changes</content>
  <parameter name="filePath">/Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant/docs/SECURITY.md
