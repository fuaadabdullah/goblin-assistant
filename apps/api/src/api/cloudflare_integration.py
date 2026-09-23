"""
Cloudflare integration for security, CDN, DDoS protection, and tunnel support
"""

import os
from typing import Any, Dict

import httpx
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class CloudflareSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for Cloudflare security features"""

    def __init__(self, app):
        super().__init__(app)
        self.cf_api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.cf_zone_id = os.getenv("CLOUDFLARE_ZONE_ID")
        self.cf_api_url = "https://api.cloudflare.com/client/v4"

    async def dispatch(self, request: Request, call_next):
        # Get Cloudflare headers
        cf_ray = request.headers.get("cf-ray")
        request.headers.get("cf-connecting-ip")
        request.headers.get("cf-ipcountry")
        request.headers.get("cf-visitor")

        # Security checks
        if cf_ray:
            # Add security headers
            response = await call_next(request)
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'"

            return response

        # If not behind Cloudflare, still add basic security headers
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"

        return response


class CloudflareCacheMiddleware(BaseHTTPMiddleware):
    """Middleware for Cloudflare caching optimization"""

    def __init__(self, app):
        super().__init__(app)
        self.cache_ttl = int(os.getenv("CLOUDFLARE_CACHE_TTL", "3600"))

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add cache headers for static content
        if request.url.path.startswith(("/static/", "/assets/", "/images/")):
            response.headers["Cache-Control"] = f"public, max-age={self.cache_ttl}"
            response.headers["CDN-Cache-Control"] = f"max-age={self.cache_ttl}"
            response.headers["Cloudflare-Cache-Control"] = f"max-age={self.cache_ttl}"

        # Add cache bypass for API endpoints
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response


class CloudflareAnalytics:
    """Cloudflare Analytics integration"""

    def __init__(self):
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.zone_id = os.getenv("CLOUDFLARE_ZONE_ID")
        self.api_url = "https://api.cloudflare.com/client/v4"

    async def get_analytics(self, since: str = "24h") -> Dict[str, Any]:
        """Get Cloudflare Analytics data"""
        if not self.api_token or not self.zone_id:
            return {"error": "Cloudflare API credentials not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        params = {
            "since": since,
            "continuous": "true",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/zones/{self.zone_id}/analytics/dashboard",
                    headers=headers,
                    params=params,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Cloudflare API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to fetch analytics: {str(e)}"}

    async def get_security_events(self, since: str = "24h") -> Dict[str, Any]:
        """Get Cloudflare security events"""
        if not self.api_token or not self.zone_id:
            return {"error": "Cloudflare API credentials not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        params = {
            "since": since,
            "continuous": "true",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/zones/{self.zone_id}/security/events",
                    headers=headers,
                    params=params,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Cloudflare API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to fetch security events: {str(e)}"}


class CloudflareDNS:
    """Cloudflare DNS management"""

    def __init__(self):
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.zone_id = os.getenv("CLOUDFLARE_ZONE_ID")
        self.api_url = "https://api.cloudflare.com/client/v4"

    async def get_dns_records(self) -> Dict[str, Any]:
        """Get DNS records for the zone"""
        if not self.api_token or not self.zone_id:
            return {"error": "Cloudflare API credentials not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/zones/{self.zone_id}/dns_records",
                    headers=headers,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Cloudflare API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to fetch DNS records: {str(e)}"}

    async def create_dns_record(
        self, name: str, type: str, content: str, ttl: int = 300
    ) -> Dict[str, Any]:
        """Create a DNS record"""
        if not self.api_token or not self.zone_id:
            return {"error": "Cloudflare API credentials not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        data = {
            "type": type,
            "name": name,
            "content": content,
            "ttl": ttl,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_url}/zones/{self.zone_id}/dns_records",
                    headers=headers,
                    json=data,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Cloudflare API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to create DNS record: {str(e)}"}


class CloudflareWAF:
    """Cloudflare Web Application Firewall management"""

    def __init__(self):
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.zone_id = os.getenv("CLOUDFLARE_ZONE_ID")
        self.api_url = "https://api.cloudflare.com/client/v4"

    async def get_firewall_rules(self) -> Dict[str, Any]:
        """Get WAF rules"""
        if not self.api_token or not self.zone_id:
            return {"error": "Cloudflare API credentials not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/zones/{self.zone_id}/firewall/rules",
                    headers=headers,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Cloudflare API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to fetch firewall rules: {str(e)}"}


# Global instances
cloudflare_analytics = CloudflareAnalytics()
cloudflare_dns = CloudflareDNS()
cloudflare_waf = CloudflareWAF()


def get_cloudflare_config() -> Dict[str, Any]:
    """Get Cloudflare configuration"""
    return {
        "api_token": bool(os.getenv("CLOUDFLARE_API_TOKEN")),
        "zone_id": bool(os.getenv("CLOUDFLARE_ZONE_ID")),
        "account_id": bool(os.getenv("CLOUDFLARE_ACCOUNT_ID")),
        "cache_ttl": int(os.getenv("CLOUDFLARE_CACHE_TTL", "3600")),
        "enabled": bool(os.getenv("CLOUDFLARE_API_TOKEN") and os.getenv("CLOUDFLARE_ZONE_ID")),
        "tunnels_enabled": bool(
            os.getenv("CLOUDFLARE_API_TOKEN") and os.getenv("CLOUDFLARE_ACCOUNT_ID")
        ),
    }
