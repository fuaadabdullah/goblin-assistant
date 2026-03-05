# Supabase Project Setup Guide

## Overview

Your GoblinOS Assistant is currently using mock authentication because the Supabase API keys are invalid. This guide will help you set up a proper Supabase project for production authentication.

## Current Status

The authentication system is working with **mock authentication fallback**. This means:
- ✅ Authentication works for development/testing
- ✅ All security measures are in place
- ❌ Not using real Supabase authentication
- ❌ Users cannot access the database
- ❌ No real user management

## Step 1: Create a Supabase Project

### Option 1: Create New Project (Recommended)
1. Go to [supabase.com](https://supabase.com)
2. Sign up/Login to your account
3. Click "New Project"
4. Fill in project details:
   - **Name**: `goblin-assistant` (or your preferred name)
   - **Database Password**: Choose a strong password
   - **Region**: Select the closest region to your users
5. Click "Create new project"

### Option 2: Use Existing Project
If you already have a Supabase project, you can use it. Just make sure authentication is enabled.

## Step 2: Configure Authentication

### Enable Email Authentication
1. In your Supabase dashboard, go to **Authentication** → **Settings**
2. Under **Auth Providers**, ensure **Email** is enabled
3. Configure the following settings:
   - **Enable email confirmations**: ✅ Enabled (recommended for production)
   - **Enable email change confirmations**: ✅ Enabled
   - **Enable password recovery**: ✅ Enabled
   - **Minimum password length**: 6 (matches our validation)

### Configure Site URL
1. In **Authentication** → **Settings** → **Site URL**
2. Set your site URL:
   - **Development**: `http://localhost:3002`
   - **Production**: Your actual domain (e.g., `https://yourapp.com`)

### Configure Redirect URLs (if using OAuth)
1. In **Authentication** → **Settings** → **Redirect URLs**
2. Add your redirect URLs:
   - `http://localhost:3002/auth/callback`
   - `https://yourdomain.com/auth/callback`

## Step 3: Get Your API Keys

### Get Project URL and Keys
1. In your Supabase dashboard, go to **Settings** → **API**
2. Copy the following values:

**Project URL**: `https://your-project-id.supabase.co`
**anon/public key**: The long JWT token starting with `eyJ...`
**service_role key**: The long JWT token (keep this secret!)

## Step 4: Update Environment Variables

### Update `.env.local`
Replace the current Supabase values in your `.env.local` file:

```bash
# Replace these lines:
NEXT_PUBLIC_SUPABASE_URL=https://dhxoowakvmobjxsffpst.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRoeG9vd2Frdm1vYmp4c2ZmcHN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzUxMzY4MzAsImV4cCI6MjA1MDcxMjgzMH0.2ccc399d27a2ed3095855f33ada0b7b3f20931bbaf8bb5f33ada0b7b3f20931bbaf8bb5f99e6ddb8b5ead7e12
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRoeG9vd2Frdm1vYmp4c2ZmcHN0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNTEzNjgzMCwiZXhwIjoyMDUwNzEyODMwfQ.2ccc399d27a2ed3095855f33ada0b7b3f20931bbaf8bb5f33ada0b7b3f20931bbaf8bb5f99e6ddb8b5ead7e12

# With your new values:
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_new_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_new_service_role_key_here
```

## Step 5: Restart the Application

```bash
# Stop the current development server (Ctrl+C)
# Then restart it:
cd apps/goblin-assistant
npm run dev
```

## Step 6: Test the Configuration

Run the authentication test:
```bash
node test-auth.js
```

You should see:
```
🧪 Testing GoblinOS Assistant Authentication...

1. Checking Supabase configuration... ✅
2. Testing user registration... ✅ (with Supabase)
3. Testing user login... ✅ (with Supabase)

🎉 Authentication tests completed!
```

## Step 7: Verify in Supabase Dashboard

1. Go to your Supabase dashboard → **Authentication** → **Users**
2. You should see your test users appear there
3. Check **Database** → **Tables** to see if user data is being stored

## Troubleshooting

### "Invalid API key" Error
- Double-check that you copied the keys correctly from Supabase dashboard
- Ensure you're using the **anon** key for `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Make sure the project is not paused

### "Email not confirmed" Error
- If you enabled email confirmations, users need to verify their email
- For development, you can disable email confirmations temporarily

### CORS Issues
- Add your domain to the allowed origins in Supabase settings
- For localhost development, ensure `http://localhost:3002` is allowed

### Database Connection Issues
- Check your database password in Supabase settings
- Ensure your IP is allowed (or use connection pooling)

## Optional: Configure OAuth Providers

### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs: `https://your-project-id.supabase.co/auth/v1/callback`
6. In Supabase: **Authentication** → **Providers** → **Google**
   - Enable Google provider
   - Add your Client ID and Client Secret

### GitHub OAuth
1. Go to GitHub → **Settings** → **Developer settings** → **OAuth Apps**
2. Create a new OAuth App
3. Set Authorization callback URL: `https://your-project-id.supabase.co/auth/v1/callback`
4. In Supabase: **Authentication** → **Providers** → **GitHub**
   - Enable GitHub provider
   - Add your Client ID and Client Secret

## Environment Variables Summary

```bash
# Required for Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Optional: For production
NEXT_PUBLIC_APP_URL=https://yourdomain.com
```

## Next Steps

1. ✅ Set up Supabase project
2. ✅ Configure authentication
3. ✅ Update environment variables
4. ✅ Test the setup
5. 🔄 Deploy to production (when ready)
6. 🔄 Set up monitoring and backups

## Security Notes

- Never commit `.env.local` to version control
- Keep the service role key secret (only used server-side)
- Regularly rotate your API keys
- Use environment-specific keys for different deployments

---

**Need Help?** Check the Supabase documentation at [supabase.com/docs](https://supabase.com/docs) or refer to `AUTHENTICATION_SETUP.md` for more details.
