"""
Cloudflare integration for security, CDN, DDoS protection, and tunnel support
"""

import os
import json
from typing import Dict, Any, Optional
import httpx
from fastapi import Request, Response
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
        cf_connecting_ip = request.headers.get("cf-connecting-ip")
        cf_country = request.headers.get("cf-ipcountry")
        cf_visitor = request.headers.get("cf-visitor")

        # Security checks
        if cf_ray:
            # Add security headers
            response = await call_next(request)
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
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


class CloudflareTunnelMiddleware(BaseHTTPMiddleware):
    """Middleware for Cloudflare Tunnel support"""

    def __init__(self, app):
        super().__init__(app)
        self.kamatera_server1 = os.getenv(
            "KAMATERA_SERVER1_URL", "http://192.175.23.150:8002"
        )
        self.kamatera_server2 = os.getenv(
            "KAMATERA_SERVER2_URL", "http://45.61.51.220:8000"
        )
        self.kamatera_redis = os.getenv(
            "KAMATERA_REDIS_URL", "http://45.61.51.220:6379"
        )
        self.kamatera_postgres = os.getenv(
            "KAMATERA_POSTGRES_URL", "http://45.61.51.220:5432"
        )

    async def dispatch(self, request: Request, call_next):
        # Add Kamatera service information to response headers
        response = await call_next(request)

        # Add service discovery headers
        response.headers["X-Kamatera-Server1"] = self.kamatera_server1
        response.headers["X-Kamatera-Server2"] = self.kamatera_server2
        response.headers["X-Kamatera-Redis"] = self.kamatera_redis
        response.headers["X-Kamatera-Postgres"] = self.kamatera_postgres

        # Add tunnel-specific headers if behind tunnel
        cf_ray = request.headers.get("cf-ray")
        if cf_ray:
            response.headers["X-CF-Ray"] = cf_ray
            response.headers["X-Tunnel-Enabled"] = "true"

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


class CloudflareTunnelManager:
    """Cloudflare Tunnel management for Kamatera servers"""

    def __init__(self):
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.api_url = "https://api.cloudflare.com/client/v4"

    async def get_tunnels(self) -> Dict[str, Any]:
        """Get list of Cloudflare tunnels"""
        if not self.api_token or not self.account_id:
            return {"error": "Cloudflare API credentials not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/accounts/{self.account_id}/tunnels",
                    headers=headers,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Cloudflare API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to fetch tunnels: {str(e)}"}

    async def check_tunnel_health(self, tunnel_hostname: str) -> Dict[str, Any]:
        """Check health of a specific tunnel endpoint"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://{tunnel_hostname}/health",
                    headers={"User-Agent": "Goblin-Assistant/1.0"},
                )

                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "response_time": response.elapsed.total_seconds(),
                    }
                else:
                    return {"status": "unhealthy", "status_code": response.status_code}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_kamatera_services_health(self) -> Dict[str, Any]:
        """Check health of all Kamatera services through tunnels"""
        services = {
            "server1_ollama": os.getenv(
                "KAMATERA_SERVER1_TUNNEL", "server1.goblin-assistant.dev"
            ),
            "server1_llamacpp": os.getenv(
                "KAMATERA_LLAMA_CPP_TUNNEL", "server1.goblin-assistant.dev"
            ),
            "server2_router": os.getenv(
                "KAMATERA_SERVER2_TUNNEL", "server2.goblin-assistant.dev"
            ),
            "server2_redis": os.getenv(
                "KAMATERA_REDIS_TUNNEL", "redis.goblin-assistant.dev"
            ),
            "server2_postgres": os.getenv(
                "KAMATERA_POSTGRES_TUNNEL", "postgres.goblin-assistant.dev"
            ),
        }

        health_status = {}
        for service_name, tunnel_hostname in services.items():
            health_status[service_name] = await self.check_tunnel_health(
                tunnel_hostname
            )

        return {
            "timestamp": json.dumps(
                {"iso": "2025-12-18T03:03:56Z", "unix": 1734483836}
            ),
            "services": health_status,
            "overall_status": "healthy"
            if all(s["status"] == "healthy" for s in health_status.values())
            else "degraded",
        }


# Global instances
cloudflare_analytics = CloudflareAnalytics()
cloudflare_dns = CloudflareDNS()
cloudflare_waf = CloudflareWAF()
cloudflare_tunnel_manager = CloudflareTunnelManager()


def get_cloudflare_config() -> Dict[str, Any]:
    """Get Cloudflare configuration"""
    return {
        "api_token": bool(os.getenv("CLOUDFLARE_API_TOKEN")),
        "zone_id": bool(os.getenv("CLOUDFLARE_ZONE_ID")),
        "account_id": bool(os.getenv("CLOUDFLARE_ACCOUNT_ID")),
        "cache_ttl": int(os.getenv("CLOUDFLARE_CACHE_TTL", "3600")),
        "kamatera_server1": os.getenv("KAMATERA_SERVER1_URL"),
        "kamatera_server2": os.getenv("KAMATERA_SERVER2_URL"),
        "kamatera_redis": os.getenv("KAMATERA_REDIS_URL"),
        "kamatera_postgres": os.getenv("KAMATERA_POSTGRES_URL"),
        "enabled": bool(
            os.getenv("CLOUDFLARE_API_TOKEN") and os.getenv("CLOUDFLARE_ZONE_ID")
        ),
        "tunnels_enabled": bool(
            os.getenv("CLOUDFLARE_API_TOKEN") and os.getenv("CLOUDFLARE_ACCOUNT_ID")
        ),
    }


async def get_kamatera_health_status() -> Dict[str, Any]:
    """Get comprehensive health status of all Kamatera services"""
    return await cloudflare_tunnel_manager.get_kamatera_services_health()
