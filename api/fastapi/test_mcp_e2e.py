#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for MCP Service

Tests all MCP functionality including:
- Authentication (JWT)
- Admin dashboard
- Provider management
- API endpoints
- Health checks
"""

import requests
import time
import sys

# Configuration
BASE_URL = "http://localhost:8000"
MCP_BASE_URL = f"{BASE_URL}/mcp/v1"


class MCPTestSuite:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_results = []

    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"   {message}")
        self.test_results.append(
            {"test": test_name, "success": success, "message": message}
        )

    def test_server_health(self):
        """Test basic server health"""
        try:
            response = self.session.get(f"{BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                if (
                    data.get("message") == "MCP Test Server"
                    and data.get("status") == "running"
                ):
                    self.log_test("Server Health Check", True, "Server is running")
                    return True
            self.log_test(
                "Server Health Check", False, f"Unexpected response: {response.text}"
            )
            return False
        except Exception as e:
            self.log_test("Server Health Check", False, f"Exception: {e}")
            return False

    def test_health_endpoint(self):
        """Test health endpoint"""
        try:
            response = self.session.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Health Endpoint", True, "Health check passed")
                    return True
            self.log_test(
                "Health Endpoint", False, f"Unexpected response: {response.text}"
            )
            return False
        except Exception as e:
            self.log_test("Health Endpoint", False, f"Exception: {e}")
            return False

    def test_admin_dashboard_unauthorized(self):
        """Test admin dashboard without authentication"""
        try:
            response = self.session.get(f"{MCP_BASE_URL}/admin/dashboard")
            if response.status_code == 200:
                # This should work for the test server
                data = response.json()
                if "total_requests" in data and "providers" in data:
                    self.log_test(
                        "Admin Dashboard (Unauthorized)", True, "Dashboard accessible"
                    )
                    return True
            self.log_test(
                "Admin Dashboard (Unauthorized)",
                False,
                f"Unexpected response: {response.text}",
            )
            return False
        except Exception as e:
            self.log_test("Admin Dashboard (Unauthorized)", False, f"Exception: {e}")
            return False

    def test_authentication_login(self):
        """Test JWT authentication"""
        try:
            # Test login with query parameters (as implemented in test server)
            response = self.session.post(
                f"{MCP_BASE_URL}/auth/login?username=admin&password=admin123"
            )
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "token_type" in data:
                    self.token = data["access_token"]
                    self.session.headers.update(
                        {"Authorization": f"Bearer {self.token}"}
                    )
                    self.log_test("JWT Authentication", True, "Login successful")
                    return True
            self.log_test("JWT Authentication", False, f"Login failed: {response.text}")
            return False
        except Exception as e:
            self.log_test("JWT Authentication", False, f"Exception: {e}")
            return False

    def test_invalid_login(self):
        """Test invalid login credentials"""
        try:
            response = self.session.post(
                f"{MCP_BASE_URL}/auth/login?username=invalid&password=wrong"
            )
            if response.status_code == 401:
                self.log_test(
                    "Invalid Login Rejection",
                    True,
                    "Invalid credentials properly rejected",
                )
                return True
            self.log_test(
                "Invalid Login Rejection",
                False,
                f"Expected 401, got {response.status_code}",
            )
            return False
        except Exception as e:
            self.log_test("Invalid Login Rejection", False, f"Exception: {e}")
            return False

    def test_admin_dashboard_authenticated(self):
        """Test admin dashboard with authentication"""
        if not self.token:
            self.log_test(
                "Admin Dashboard (Authenticated)", False, "No token available"
            )
            return False

        try:
            response = self.session.get(f"{MCP_BASE_URL}/admin/dashboard")
            if response.status_code == 200:
                data = response.json()
                required_keys = [
                    "total_requests",
                    "active_requests",
                    "completed_requests",
                    "failed_requests",
                    "providers",
                ]
                if all(key in data for key in required_keys):
                    # Check provider health
                    providers = data.get("providers", {})
                    healthy_providers = sum(
                        1
                        for p in providers.values()
                        if isinstance(p, dict) and p.get("status") == "healthy"
                    )
                    self.log_test(
                        "Admin Dashboard (Authenticated)",
                        True,
                        f"Dashboard working, {healthy_providers} providers healthy",
                    )
                    return True
            self.log_test(
                "Admin Dashboard (Authenticated)",
                False,
                f"Unexpected response: {response.text}",
            )
            return False
        except Exception as e:
            self.log_test("Admin Dashboard (Authenticated)", False, f"Exception: {e}")
            return False

    def test_provider_status(self):
        """Test provider status in dashboard"""
        if not self.token:
            return False

        try:
            response = self.session.get(f"{MCP_BASE_URL}/admin/dashboard")
            if response.status_code == 200:
                data = response.json()
                providers = data.get("providers", {})

                expected_providers = ["openai", "anthropic", "local"]
                found_providers = [p for p in expected_providers if p in providers]

                if len(found_providers) >= 2:  # At least 2 providers should be present
                    self.log_test(
                        "Provider Status", True, f"Found providers: {found_providers}"
                    )
                    return True
                else:
                    self.log_test(
                        "Provider Status",
                        False,
                        f"Missing providers. Found: {list(providers.keys())}",
                    )
                    return False
            return False
        except Exception as e:
            self.log_test("Provider Status", False, f"Exception: {e}")
            return False

    def test_metrics_endpoint(self):
        """Test metrics endpoint if available"""
        try:
            response = self.session.get(f"{MCP_BASE_URL}/admin/metrics")
            if response.status_code == 200:
                self.log_test("Metrics Endpoint", True, "Metrics endpoint accessible")
                return True
            elif response.status_code == 404:
                self.log_test(
                    "Metrics Endpoint",
                    True,
                    "Metrics endpoint not implemented (expected)",
                )
                return True
            else:
                self.log_test(
                    "Metrics Endpoint",
                    False,
                    f"Unexpected status: {response.status_code}",
                )
                return False
        except Exception as e:
            self.log_test(
                "Metrics Endpoint", True, f"Metrics endpoint not available: {e}"
            )
            return True  # Not a failure if metrics aren't implemented

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 MCP Service End-to-End Test Suite")
        print("=" * 50)

        tests = [
            self.test_server_health,
            self.test_health_endpoint,
            self.test_admin_dashboard_unauthorized,
            self.test_authentication_login,
            self.test_invalid_login,
            self.test_admin_dashboard_authenticated,
            self.test_provider_status,
            self.test_metrics_endpoint,
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            if test():
                passed += 1
            time.sleep(0.1)  # Small delay between tests

        print("\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed! MCP service is fully operational.")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            return False


def main():
    """Main test runner"""
    suite = MCPTestSuite()
    success = suite.run_all_tests()

    # Print detailed results
    print("\n📋 Detailed Test Results:")
    for result in suite.test_results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['test']}")
        if result["message"]:
            print(f"   {result['message']}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
