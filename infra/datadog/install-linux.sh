#!/bin/bash
# Install Datadog Agent on Linux (Production/VM)
# Run with: bash infra/datadog/install-linux.sh

set -e

echo "🐕 Installing Datadog Agent on Linux..."

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "❌ Cannot detect OS"
    exit 1
fi

# Install based on OS
case $OS in
    ubuntu|debian)
        # Install on Ubuntu/Debian
        echo "📦 Installing on Ubuntu/Debian..."
        sudo apt-get update
        sudo apt-get install -y apt-transport-https ca-certificates curl gnupg

        # Add Datadog GPG key
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://keys.datadoghq.com/DATADOG_APT_KEY_CURRENT.public | sudo gpg --dearmor -o /etc/apt/keyrings/datadog.gpg

        # Add Datadog repository
        echo "deb [signed-by=/etc/apt/keyrings/datadog.gpg] https://apt.datadoghq.com/ stable main" | sudo tee /etc/apt/sources.list.d/datadog.list

        sudo apt-get update
        sudo apt-get install -y datadog-agent
        ;;

    centos|rhel|fedora)
        # Install on CentOS/RHEL/Fedora
        echo "📦 Installing on CentOS/RHEL/Fedora..."
        sudo rpm --import https://keys.datadoghq.com/DATADOG_RPM_KEY_CURRENT.public

        # Create yum repo
        sudo tee /etc/yum.repos.d/datadog.repo <<EOF
[datadog]
name=Datadog, Inc.
baseurl=https://yum.datadoghq.com/stable/7/x86_64/
enabled=1
gpgcheck=1
repo_gpgcheck=0
gpgkey=https://keys.datadoghq.com/DATADOG_RPM_KEY_CURRENT.public
EOF

        sudo yum install -y datadog-agent
        ;;

    *)
        echo "❌ Unsupported OS: $OS"
        echo "Please visit: https://docs.datadoghq.com/agent/installation/"
        exit 1
        ;;
esac

# Copy configuration
sudo mkdir -p /etc/datadog-agent
sudo cp infra/datadog/datadog.yaml /etc/datadog-agent/datadog.yaml

# Set environment variables
echo "⚠️  Please set DATADOG_API_KEY environment variable:"
echo "export DATADOG_API_KEY=your-api-key-here"
echo "export DD_ENV=prod"
echo ""
echo "Or add to /etc/environment or systemd service"

# Enable and start service
sudo systemctl enable datadog-agent
sudo systemctl start datadog-agent

echo "✅ Datadog Agent installed and started!"
echo "Check status: sudo systemctl status datadog-agent"
echo "View logs: sudo journalctl -u datadog-agent -f"
