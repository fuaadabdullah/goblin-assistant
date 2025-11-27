# Production Deployment Guide - Datadog Monitoring Setup

## Overview

This guide covers the complete setup for deploying the Goblin Assistant with Datadog error tracking and monitoring to production.

## Prerequisites

- Datadog account with RUM and Logs enabled
- Vercel/Netlify account for deployment
- Access to production environment variables

---

## 1. Set Up Datadog Credentials

### Step 1.1: Create Datadog Application

1. Go to [Datadog RUM](https://app.datadoghq.com/rum/applications)
2. Click "Add Application"
3. Fill in:
   - **Application Name**: `Goblin Assistant Frontend`
   - **Application Type**: `Web`
   - **Environment**: `production` (and `staging` for staging)
4. Copy the generated credentials

### Step 1.2: Configure Environment Variables

#### For Production (`.env.production`):

```bash
# Datadog RUM Configuration (Frontend)
VITE_DD_APPLICATION_ID=your_actual_application_id_here
VITE_DD_CLIENT_TOKEN=your_actual_client_token_here
VITE_DD_ENV=production
VITE_DD_VERSION=1.0.0

# Backend Datadog (if using)
DD_API_KEY=your_datadog_api_key
DD_APP_KEY=your_datadog_app_key
```

#### For Staging (`.env.staging`):

```bash
# Datadog RUM Configuration (Frontend)
VITE_DD_APPLICATION_ID=your_staging_application_id_here
VITE_DD_CLIENT_TOKEN=your_staging_client_token_here
VITE_DD_ENV=staging
VITE_DD_VERSION=1.0.0
```

### Step 1.3: Set Environment Variables in Hosting Platform

#### Vercel:

```bash
vercel env add VITE_DD_APPLICATION_ID production
vercel env add VITE_DD_CLIENT_TOKEN production
vercel env add VITE_DD_ENV production
vercel env add VITE_DD_VERSION production
```

#### Netlify:

Add to Site Settings > Environment Variables:
- `VITE_DD_APPLICATION_ID`
- `VITE_DD_CLIENT_TOKEN`
- `VITE_DD_ENV`
- `VITE_DD_VERSION`

---

## 2. Test in Staging Environment

### Step 2.1: Deploy to Staging
```bash
# Using the deployment script
./deploy.sh staging

# Or manually with Vercel
vercel --prod=false

# Or manually with Netlify
netlify deploy --dir=dist
```

### Step 2.2: Run Automated Tests
```bash
# Run the Datadog integration test
./test-datadog.sh
```

### Step 2.3: Manual Testing Checklist
- [ ] Open staging URL in browser
- [ ] Check browser console for Datadog initialization messages
- [ ] Trigger API errors (try when backend is down)
- [ ] Navigate to invalid routes
- [ ] Check Datadog RUM dashboard for:
  - [ ] User sessions appearing
  - [ ] Page views recorded
  - [ ] Any errors logged

### Step 2.4: Verify Error Tracking
1. Go to [Datadog RUM Explorer](https://app.datadoghq.com/rum/explorer)
2. Filter by:
   - Service: `goblin-assistant-frontend`
   - Environment: `staging`
3. Look for:
   - Error events
   - User sessions
   - Performance metrics

---

## 3. Monitor Production Dashboard

### Step 3.1: Access Datadog Dashboards

#### Real User Monitoring (RUM):
- **URL**: https://app.datadoghq.com/rum/overview
- **Key Metrics**:
  - Page views and unique visitors
  - Core Web Vitals (LCP, FID, CLS)
  - Error rates
  - User session recordings

#### Browser Logs:
- **URL**: https://app.datadoghq.com/logs
- **Filters**:
  - Service: `goblin-assistant-frontend`
  - Source: `browser`
  - Status: `error`

### Step 3.2: Key Metrics to Monitor
- **Error Rate**: Target < 1%
- **API Call Success Rate**: Target > 99%
- **Page Load Performance**: LCP < 2.5s
- **User Frustration Signals**: Monitor rage clicks, dead clicks

### Step 3.3: Create Custom Dashboards
1. Go to Dashboards > New Dashboard
2. Add widgets for:
   - Error rate over time
   - API response times
   - User session duration
   - Top error pages

---

## 4. Set Up Alerts and Monitors

### Step 4.1: Error Rate Alert
1. Go to Monitors > New Monitor
2. Select "Metric Monitor"
3. Configure:
   - **Metric**: `rum.errors.error_rate`
   - **Service**: `goblin-assistant-frontend`
   - **Environment**: `production`
   - **Threshold**: > 5% over 5 minutes
   - **Alert Message**: "High error rate detected in production"

### Step 4.2: API Failure Alert
1. Create a new monitor for API errors:
   - **Metric**: `rum.errors.count`
   - **Filter**: `resource.url:*api*`
   - **Threshold**: > 10 errors per minute
   - **Alert**: "API failures spiking in production"

### Step 4.3: Performance Alert
1. Create LCP performance alert:
   - **Metric**: `rum.performance.lcp`
   - **Threshold**: > 4 seconds (p75)
   - **Alert**: "Poor page load performance detected"

### Step 4.4: Configure Alert Channels
- **Email**: Team distribution list
- **Slack**: #alerts channel
- **PagerDuty**: For critical production issues

---

## 5. Production Deployment

### Step 5.1: Final Environment Check
```bash
# Verify environment variables
echo $VITE_DD_APPLICATION_ID
echo $VITE_DD_CLIENT_TOKEN
echo $VITE_DD_ENV
```

### Step 5.2: Deploy to Production
```bash
# Using the Netlify deployment script (recommended)
./deploy-netlify.sh

# Or using the general deployment script
./deploy.sh netlify

# For staging deployment
./deploy-netlify.sh --staging
./deploy.sh netlify-staging
```

### Step 5.3: Set Environment Variables in Netlify
After deployment, configure environment variables in Netlify dashboard:

1. Go to your Netlify site dashboard
2. Navigate to Site Settings > Environment Variables
3. Add the following variables:
   - `VITE_DD_APPLICATION_ID` = your Datadog Application ID
   - `VITE_DD_CLIENT_TOKEN` = your Datadog Client Token
   - `VITE_DD_ENV` = production
   - `VITE_DD_VERSION` = 1.0.0
   - `VITE_FASTAPI_URL` = https://your-api-domain.com
   - `VITE_GOBLIN_RUNTIME` = fastapi
   - `VITE_MOCK_API` = false

### Step 5.4: Post-Deployment Verification
1. **Check Application Loads**: Visit the Netlify deployment URL
2. **Verify Datadog Data**: Check RUM dashboard for new data
3. **Test Error Scenarios**: Try error conditions safely
4. **Monitor for 24 Hours**: Watch dashboards for anomalies

---

## 6. Troubleshooting

### Common Issues:

#### "Datadog RUM not available" in console:
- Check environment variables are set correctly
- Verify VITE_ prefix is used (not NEXT_PUBLIC_)
- Ensure Datadog packages are installed

#### No data in Datadog dashboard:
- Wait 5-10 minutes for data to appear
- Check application ID and client token are correct
- Verify environment name matches dashboard filters

#### CORS errors with Datadog:
- Ensure `datadoghq.com` is allowed in CSP headers
- Check if ad-blockers are interfering

#### High error rates:
- Check browser compatibility (ES2020+ support)
- Verify API endpoints are responding
- Check for JavaScript runtime errors

---

## 7. Maintenance

### Weekly Checks:
- [ ] Review error trends in Datadog
- [ ] Check alert configurations
- [ ] Update Datadog RUM version if needed
- [ ] Monitor Core Web Vitals

### Monthly Reviews:
- [ ] Analyze top error patterns
- [ ] Review performance metrics
- [ ] Update alert thresholds based on data
- [ ] Check Datadog billing usage

---

## Support Resources

- **Datadog RUM Documentation**: https://docs.datadoghq.com/real_user_monitoring/
- **Browser Logs Setup**: https://docs.datadoghq.com/logs/log_collection/javascript/
- **Alert Configuration**: https://docs.datadoghq.com/monitors/

---

*Last Updated: November 27, 2025*
