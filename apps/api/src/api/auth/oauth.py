import httpx
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
import secrets
import base64
import hashlib
from urllib.parse import urlencode
from pathlib import Path

# Load environment variables from the backend directory
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / ".env"
load_dotenv(env_file)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback"
)


class GoogleOAuth:
    @staticmethod
    def get_authorization_url(state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL
        """
        if not GOOGLE_CLIENT_ID:
            raise ValueError("GOOGLE_CLIENT_ID not configured")

        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state
        else:
            params["state"] = secrets.token_urlsafe(32)

        return f"{base_url}?{urlencode(params)}"

    @staticmethod
    async def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access token
        """
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": GOOGLE_REDIRECT_URI,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    # Log the error for debugging
                    print(
                        f"Google OAuth error: {response.status_code} - {response.text}"
                    )
                    return None
        except Exception as e:
            print(f"Exception during token exchange: {e}")
            return None

    @staticmethod
    async def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google OAuth token and return user info
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"access_token": token},
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return None
        except Exception:
            return None

    @staticmethod
    async def get_user_info(access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed user info from Google using access token
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return None
        except Exception:
            return None
