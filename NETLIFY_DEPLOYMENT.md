---
title: "NETLIFY DEPLOYMENT"
description: "Netlify Deployment (DEPRECATED)"
---

# Netlify Deployment (DEPRECATED)

Netlify deployment support for the Goblin Assistant has been removed. This file has been retained for historical reference only.

Recommended alternatives:

- Vercel (preferred)
- Fly
- Custom hosting (e.g., S3/CloudFront, Cloudflare Pages)

For deployment instructions, please consult the general deployment guide (`deploy.sh`) or the relevant provider's docs (e.g., `./deploy.sh vercel`).

If you still need to migrate a Netlify deployment, port the environment variables from `.env.production` into your hosting provider's dashboard and follow the provider's deployment steps.
