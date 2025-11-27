# Netlify Deployment Guide

This guide covers deploying the Goblin Assistant to Netlify with Datadog monitoring.

## Prerequisites

- Netlify account
- Datadog account with RUM enabled
- Node.js and npm installed

## Quick Start

### 1. Login to Netlify

```bash
netlify login
```

### 2. Configure Environment Variables

Update your `.env.production` file with actual Datadog credentials:

```bash
# Datadog RUM Configuration (Frontend)
VITE_DD_APPLICATION_ID=your_actual_application_id_here
VITE_DD_CLIENT_TOKEN=your_actual_client_token_here
VITE_DD_ENV=production
VITE_DD_VERSION=1.0.0

# Backend Configuration
VITE_FASTAPI_URL=https://your-api-domain.com
VITE_GOBLIN_RUNTIME=fastapi
VITE_MOCK_API=false
```

### 3. Deploy to Production

```bash
# Deploy to production
./deploy-netlify.sh

# Deploy to staging
./deploy-netlify.sh --staging
```

## Manual Deployment

If you prefer manual deployment:

```bash
# Build the application
npm run build

# Deploy to Netlify
netlify deploy --prod --dir=dist
```

## Environment Variables Setup

### In Netlify Dashboard

1. Go to Site Settings > Environment Variables
2. Add variables from your `.env.production` file
3. **Important**: Variables starting with `VITE_` are automatically available to your frontend code

### Required Variables

- `VITE_DD_APPLICATION_ID` - Datadog RUM Application ID
- `VITE_DD_CLIENT_TOKEN` - Datadog RUM Client Token
- `VITE_DD_ENV` - Environment (production/staging)
- `VITE_DD_VERSION` - Application version
- `VITE_FASTAPI_URL` - Backend API URL
- `VITE_GOBLIN_RUNTIME` - Runtime type (fastapi)
- `VITE_MOCK_API` - Whether to use mock API (false for production)

## Testing Deployment

### Local Testing

```bash
# Test the build locally
./test-datadog.sh
```

### Staging Deployment

```bash
# Deploy to staging branch
./deploy-netlify.sh --staging

# This creates a staging deployment at: https://staging--your-site-name.netlify.app
```

## Monitoring

After deployment:

1. **Check Application**: Visit the Netlify deployment URL
2. **Verify Datadog**: Check RUM dashboard for user sessions
3. **Test Errors**: Try invalid routes or API failures
4. **Monitor Logs**: Check Datadog Logs for error events

## Troubleshooting

### Build Fails:
- Ensure all environment variables are set
- Check that `netlify.toml` exists
- Verify Node.js version (18+ recommended)

### Datadog Not Working:
- Check environment variables are prefixed with `VITE_`
- Verify Datadog Application ID and Client Token
- Check browser console for initialization errors

### API Not Working:
- Ensure `VITE_FASTAPI_URL` is set correctly
- Check CORS configuration on your backend
- Verify backend is deployed and accessible

## Netlify Configuration

The `netlify.toml` file includes:
- Build settings (`npm run build`)
- Publish directory (`dist`)
- SPA redirects (handle client-side routing)
- Security headers
- Cache optimization for assets

## Support

For issues:
1. Check Netlify deployment logs
2. Verify environment variables
3. Test locally with `./test-datadog.sh`
4. Check Datadog dashboard for errors
