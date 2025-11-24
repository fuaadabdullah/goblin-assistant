#!/usr/bin/env python3
"""
Securely store OpenAI API key in HashiCorp Vault
"""

import os
import sys
from vault_client import VaultClient


def main():
    # Check if Vault environment variables are set
    if not os.getenv("VAULT_ADDR") or not os.getenv("VAULT_TOKEN"):
        print("❌ ERROR: VAULT_ADDR and VAULT_TOKEN environment variables must be set")
        print("Example:")
        print("export VAULT_ADDR='https://your-vault-server.com:8200'")
        print("export VAULT_TOKEN='your-vault-token'")
        sys.exit(1)

    try:
        # Initialize Vault client
        vault = VaultClient()

        # OpenAI API key and organization ID from user input
        openai_key = "ATCTT3xFfGN07T9k8uYwStcYJ2aznVlxYbrJXKl3mMSn09B0Q6cC1_Zit3LTxaXxle8c2UuMQxkmYS5-AzAtPQqcH0lYuvE3Q-zO8_ZbsjTEukq16gEaoGKh_RluCScxNgquHJE2WdMCWkjiMfY2QJIXdDCuoYnsFJjREOGGe1IsLLiF_2-m8FA=8F0B1A6"
        openai_org = "4a18c94b-effe-41b5-9d48-b0ea38a082f4"

        # Store in Vault
        secrets = {"OPENAI_API_KEY": openai_key, "OPENAI_ORGANIZATION_ID": openai_org}

        vault_path = "secret/goblin-assistant/openai"
        success = vault.set_secret(vault_path, secrets)

        if success:
            print("✅ Successfully stored OpenAI API key and Organization ID in Vault")
            print(f"📍 Vault path: {vault_path}")
            print("🔒 Key stored securely - never commit to version control!")
        else:
            print("❌ Failed to store secrets in Vault")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
