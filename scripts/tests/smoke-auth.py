#!/usr/bin/env python3
"""Run register -> login -> refresh -> logout -> login against a live API."""

from __future__ import annotations

import argparse
import os

from smoke_support import (
    SmokeFailure,
    login_user,
    register_user,
    request_json,
    require_success,
    unique_credentials,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-url",
        default=os.getenv("SMOKE_BACKEND_URL", "http://127.0.0.1:8001"),
    )
    args = parser.parse_args()
    api_base_url = f"{args.backend_url.rstrip('/')}/api/v1"
    email, password = unique_credentials()

    try:
        print(f"Auth smoke against {api_base_url}")

        print("[1/5] Register")
        registration = register_user(api_base_url, email, password)
        if not isinstance(registration.get("refresh_token"), str):
            raise SmokeFailure("Register response did not include data.refresh_token")

        print("[2/5] Login")
        login = login_user(api_base_url, email, password)
        refresh_token = login.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise SmokeFailure("Login response did not include data.refresh_token")

        print("[3/5] Refresh")
        refresh_body = require_success(
            "Refresh",
            request_json(
                f"{api_base_url}/auth/refresh",
                method="POST",
                payload={"refresh_token": refresh_token},
            ),
        )
        refresh_data = refresh_body.get("data")
        if not isinstance(refresh_data, dict):
            raise SmokeFailure("Refresh response did not include data")
        access_token = refresh_data.get("access_token")
        refreshed_token = refresh_data.get("refresh_token")
        if not isinstance(access_token, str) or not isinstance(refreshed_token, str):
            raise SmokeFailure("Refresh response did not include both tokens")

        print("[4/5] Logout")
        require_success(
            "Logout",
            request_json(
                f"{api_base_url}/auth/logout",
                method="POST",
                access_token=access_token,
            ),
        )
        revoked_status, _ = request_json(
            f"{api_base_url}/auth/refresh",
            method="POST",
            payload={"refresh_token": refreshed_token},
        )
        if revoked_status != 401:
            raise SmokeFailure(
                f"Logged-out refresh token was not revoked (expected 401, got {revoked_status})"
            )

        print("[5/5] Login again")
        final_login = login_user(api_base_url, email, password)
        if not final_login.get("access_token"):
            raise SmokeFailure("Final login returned no access token")
    except SmokeFailure as error:
        print(f"FAIL: {error}")
        return 1

    print("PASS: register -> login -> refresh -> logout -> login")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
