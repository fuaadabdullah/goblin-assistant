# Supabase SMTP Configuration for Email Confirmations

This document describes the SMTP setup required for email confirmations to work in production.

## Problem

When Supabase is configured with `autoconfirm` disabled (the secure default), new user signups require email confirmation. Without a working SMTP provider configured in Supabase, these confirmation emails are never sent, causing signups to appear successful but users cannot complete authentication.

## Solution: Configure SMTP Provider

### Option A: Resend (Recommended)

Resend is an email API service optimized for developers. It integrates directly with Supabase.

#### Setup Steps:

1. **Create Resend account and API key:**
   - Go to [resend.com](https://resend.com) and sign up
   - Create an API key in the Resend dashboard
   - Add your sending domain and verify DNS records (or use the sandbox domain for testing)

2. **Configure in Supabase Dashboard:**
   - Navigate to your Supabase project → Authentication → Settings
   - Under "External OAuth Providers" → "SMTP Settings", enter:
     - **SMTP Host:** `smtp.resend.com`
     - **SMTP Port:** `465` (SSL) or `587` (TLS)
     - **SMTP User:** `resend`
     - **SMTP Password:** Your Resend API key
     - **Sender:** The verified email address or domain (e.g., `noreply@yourdomain.com`)

3. **Environment Variables (if using proxy):**
   - Store the Resend API key in your deployment secrets
   - Supabase dashboard configuration takes precedence over env vars for SMTP

### Option B: Supabase Built-in SMTP (Default)

Supabase provides a default email service, but it may have rate limits in free tier.

#### Configuration:
- Supabase → Authentication → Settings → User Signups
- Ensure "Confirm email" is enabled (not "Auto confirm")
- The default SMTP should work out of the box with reasonable rate limits

### Environment Variables Required

```bash
# Supabase Configuration (set in Supabase dashboard or .env.local)
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# For server-side operations
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## Verification

After configuration:

1. **Test signup flow in staging:**
   - Create a test account with a real email address
   - Check inbox for confirmation email
   - Click confirmation link and verify login works

2. **Check Supabase logs:**
   - Supabase Dashboard → Logs → Auth logs
   - Look for email sending attempts and any errors

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| No email received | SMTP not configured | Check Supabase SMTP settings, verify API key |
| Email goes to spam | Missing SPF/DKIM records | Add DNS records for your sending domain |
| "Rate limit exceeded" | Too many emails | Upgrade SMTP provider tier or implement rate limiting |

## Related Files

- Frontend auth: `apps/web/src/components/auth/ModularLoginForm.tsx`
- Supabase client: `apps/web/src/lib/supabase.ts`
- Auth interceptor: `apps/web/src/lib/api/http-client.ts`
- CSRF protection: `apps/web/src/lib/api/csrf.ts` (still needed for signup/login)