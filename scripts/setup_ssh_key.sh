#!/bin/bash
# Setup SSH Key in Bitwarden Vault
# This script helps you securely store your SSH private key in Bitwarden

set -e

echo "🔑 Setting up SSH key in Bitwarden vault..."
echo ""

# Check if Bitwarden CLI is available
if ! command -v bw &> /dev/null; then
    echo "❌ Bitwarden CLI not found. Installing..."
    npm install -g @bitwarden/cli
fi

# Unlock vault
echo "🔐 Unlocking Bitwarden vault..."
export BW_SESSION=$(bw unlock --raw)

echo ""
echo "📝 Please create a new 'Secure Note' in Bitwarden with:"
echo "   Name: goblin-ssh-private-key"
echo "   Type: Secure Note"
echo ""
echo "📋 Copy and paste your SSH private key as the note content:"
echo "   (The full key including -----BEGIN OPENSSH PRIVATE KEY----- and -----END OPENSSH PRIVATE KEY-----)"
echo ""
echo "🔍 To verify the key was stored correctly:"
echo "   bw get notes goblin-ssh-private-key"
echo ""
echo "✅ Once you've added the key to Bitwarden, CircleCI will automatically retrieve it during deployment."
echo ""
echo "🔗 Don't forget to add the PUBLIC key to your GitHub account:"
echo "   GitHub → Settings → SSH and GPG keys → New SSH key"
echo ""

# Clean up
unset BW_SESSION

echo "🧹 Session cleaned up. SSH key setup complete!"
