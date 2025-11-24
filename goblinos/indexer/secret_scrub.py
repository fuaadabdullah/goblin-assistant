"""
Secret scrubbing utilities for Goblin Assistant.
Scans content for potential secrets before indexing.
"""

import re
from typing import List, Dict, Any, Tuple


class SecretScanner:
    """Scans content for potential secrets and sensitive data."""

    def __init__(self):
        # Common secret patterns
        self.secret_patterns = [
            # API keys and tokens
            (r'\bapi[_-]?key\s*[:=]\s*["\']([^"\']+)["\']', "API_KEY"),
            (r'\btoken\s*[:=]\s*["\']([^"\']+)["\']', "TOKEN"),
            (r'\bsecret\s*[:=]\s*["\']([^"\']+)["\']', "SECRET"),
            (r'\bauth[_-]?key\s*[:=]\s*["\']([^"\']+)["\']', "AUTH_KEY"),
            # Specific API key formats
            (r"\bsk-[a-zA-Z0-9]{48}\b", "OPENAI_API_KEY"),
            (r"\bAT[a-zA-Z0-9]{20,}\b", "ATLASSIAN_TOKEN"),
            (r"\bghp_[a-zA-Z0-9]{36}\b", "GITHUB_TOKEN"),
            (r"\bglpat-[a-zA-Z0-9_-]{20,}\b", "GITLAB_TOKEN"),
            # Passwords
            (r'\bpassword\s*[:=]\s*["\']([^"\']+)["\']', "PASSWORD"),
            (r'\bpasswd\s*[:=]\s*["\']([^"\']+)["\']', "PASSWORD"),
            # Private keys
            (r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "PRIVATE_KEY"),
            (r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----", "SSH_PRIVATE_KEY"),
            # Database credentials
            (r'\bDATABASE_URL\s*[:=]\s*["\']([^"\']+)["\']', "DATABASE_URL"),
            (r'\bDB_PASSWORD\s*[:=]\s*["\']([^"\']+)["\']', "DB_PASSWORD"),
            # Cloud credentials
            (r'\bAWS_ACCESS_KEY_ID\s*[:=]\s*["\']([^"\']+)["\']', "AWS_KEY"),
            (
                r'\bGOOGLE_APPLICATION_CREDENTIALS\s*[:=]\s*["\']([^"\']+)["\']',
                "GCP_CREDENTIALS",
            ),
        ]

        # Entropy-based detection for random strings
        self.high_entropy_pattern = r"\b[A-Za-z0-9+/=]{20,}\b"

        # Whitelist for known safe patterns
        self.whitelist_patterns = [
            r"\btest[_-]?key\b",
            r"\bdummy[_-]?token\b",
            r"\bexample[_-]?secret\b",
            r"\bfake[_-]?password\b",
            r"\bplaceholder\b",
            r"\bYOUR[_-]?.*[_-]?HERE\b",
        ]

    def scan_content(self, content: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Scan content for secrets.
        Returns (is_safe, findings) where is_safe is True if no secrets found.
        """
        findings = []

        # Check each pattern
        for pattern, secret_type in self.secret_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Check if it's in whitelist
                if not self._is_whitelisted(match.group(0)):
                    findings.append(
                        {
                            "type": secret_type,
                            "match": match.group(0),
                            "line": content[: match.start()].count("\n") + 1,
                            "position": match.start(),
                            "entropy_score": self._calculate_entropy(match.group(0)),
                        }
                    )

        # Check for high-entropy strings
        high_entropy_matches = re.finditer(self.high_entropy_pattern, content)
        for match in high_entropy_matches:
            candidate = match.group(0)
            entropy = self._calculate_entropy(candidate)

            # Only flag very high entropy strings
            if entropy > 4.5 and not self._is_whitelisted(candidate):
                findings.append(
                    {
                        "type": "HIGH_ENTROPY_STRING",
                        "match": candidate,
                        "line": content[: match.start()].count("\n") + 1,
                        "position": match.start(),
                        "entropy_score": entropy,
                    }
                )

        return len(findings) == 0, findings

    def _is_whitelisted(self, text: str) -> bool:
        """Check if text matches whitelist patterns."""
        for pattern in self.whitelist_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not text:
            return 0.0

        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Calculate entropy
        entropy = 0.0
        length = len(text)
        for count in char_counts.values():
            probability = count / length
            entropy -= probability * (
                probability.bit_length() - 1
            )  # log2 approximation

        return entropy

    def redact_content(self, content: str, findings: List[Dict[str, Any]]) -> str:
        """Redact found secrets from content."""
        redacted = content

        # Sort findings by position (reverse order to avoid offset issues)
        sorted_findings = sorted(findings, key=lambda x: x["position"], reverse=True)

        for finding in sorted_findings:
            start = finding["position"]
            end = start + len(finding["match"])
            redaction = f"[{finding['type']}_REDACTED]"
            redacted = redacted[:start] + redaction + redacted[end:]

        return redacted

    def get_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Get recommendations for handling findings."""
        recommendations = []

        if not findings:
            return ["✅ No secrets detected - content is safe to index"]

        type_counts = {}
        for finding in findings:
            ftype = finding["type"]
            type_counts[ftype] = type_counts.get(ftype, 0) + 1

        recommendations.append(f"⚠️  Found {len(findings)} potential secrets:")

        for ftype, count in type_counts.items():
            recommendations.append(f"  • {count} {ftype} pattern(s)")

        recommendations.extend(
            [
                "💡 Recommendations:",
                "  • Move secrets to environment variables",
                "  • Use secret management (Vault, AWS Secrets Manager)",
                "  • Add detected patterns to .gitignore",
                "  • Consider redacting sensitive content before indexing",
            ]
        )

        return recommendations
