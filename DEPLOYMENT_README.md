# Goblin Assistant Production Deployment Guide

## Build Status ✅

- **Build completed successfully** on November 27, 2025
- **Output location**: `dist/` folder
- **Build size**: 465.63 kB JS (148.75 kB gzipped), 33.92 kB CSS (7.34 kB gzipped)
- **Source maps**: Included for debugging

## Environment Configuration ✅

Production environment variables configured in `.env.production`:

- `VITE_FASTAPI_URL=https://api.goblin-assistant.com`
- `VITE_GOBLIN_RUNTIME=fastapi`
- `VITE_MOCK_API=false`
- `ENV=production`

## Deployment Instructions

### 1. Static Hosting (Recommended)

Deploy the `dist/` folder to any static hosting service:

**Vercel:**

```bash
npm i -g vercel
vercel --prod
```

**Netlify:**

```bash
npm i -g netlify-cli
netlify deploy --prod --dir=dist
```

**AWS S3 + CloudFront:**

```bash
aws s3 sync dist/ s3://your-bucket-name --delete
# Configure CloudFront distribution
```

**GitHub Pages:**

```bash
npm i -g gh-pages
gh-pages -d dist
```

### 2. Backend Requirements

Ensure your FastAPI backend is deployed and accessible at:
`https://api.goblin-assistant.com`

Required backend endpoints:

- `GET /routing/providers/:provider`
- `POST /parse`
- `POST /auth/validate`
- `GET /raptor/demo/:value`

### 3. Environment Variables

Update `.env.production` with your actual values:

```bash
# Replace with your actual backend URL
VITE_FASTAPI_URL=https://your-api-domain.com

# Set to false for production
VITE_MOCK_API=false
```

### 4. Testing Production Build

```bash
# Test locally
npx vite preview --port 4173

# Visit http://localhost:4173
```

## Build Artifacts

```
dist/
├── index.html          # Main HTML file
├── assets/
│   ├── index-*.js      # Minified JavaScript (465KB)
│   ├── index-*.css     # Minified CSS (34KB)
│   └── *.map           # Source maps for debugging
└── *.png               # Static assets
```

## Performance Optimizations ✅

- **Code splitting**: Automatic chunk splitting
- **Minification**: Terser minification enabled
- **Compression**: Gzip compression ready
- **Source maps**: Available for debugging
- **Tree shaking**: Unused code eliminated

## Security Considerations

- ✅ Environment variables properly configured
- ✅ No sensitive data in client bundle
- ✅ HTTPS required for production
- ✅ CORS configured on backend

---
**Ready for deployment! 🚀**
