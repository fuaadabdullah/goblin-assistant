#!/usr/bin/env python3
"""
Load Testing Script for Goblin Assistant
Tests authentication endpoints and system performance under concurrent load
"""

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Tuple
import json


class LoadTester:
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def make_request(
        self, method: str, endpoint: str, data: dict = None, headers: dict = None
    ) -> Tuple[float, int, str]:
        """Make a single HTTP request and return (response_time, status_code, response_text)"""
        start_time = time.time()

        try:
            url = f"{self.base_url}{endpoint}"
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    response_time = time.time() - start_time
                    return response_time, response.status, response_text
            elif method.upper() == "POST":
                async with self.session.post(
                    url, json=data, headers=headers
                ) as response:
                    response_text = await response.text()
                    response_time = time.time() - start_time
                    return response_time, response.status, response_text
        except Exception as e:
            response_time = time.time() - start_time
            return response_time, 0, str(e)

    async def test_health_endpoint(self, concurrent_users: int = 10) -> Dict:
        """Test health endpoint with concurrent users"""
        print(f"🩺 Testing health endpoint with {concurrent_users} concurrent users...")

        tasks = []
        for _ in range(concurrent_users):
            tasks.append(self.make_request("GET", "/health"))

        results = await asyncio.gather(*tasks)

        response_times = [r[0] for r in results]
        status_codes = [r[1] for r in results]
        errors = [r[2] for r in results if r[1] != 200]

        return {
            "endpoint": "/health",
            "concurrent_users": concurrent_users,
            "total_requests": len(results),
            "successful_requests": status_codes.count(200),
            "failed_requests": len([s for s in status_codes if s != 200]),
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[
                18
            ],  # 95th percentile
            "errors": errors[:5],  # Show first 5 errors
        }

    async def test_auth_registration(self, num_users: int = 5) -> Dict:
        """Test user registration with multiple users"""
        print(f"📝 Testing user registration with {num_users} users...")

        tasks = []
        for i in range(num_users):
            user_data = {
                "email": f"loadtest{i}@example.com",
                "password": "testpassword123",
                "full_name": f"Load Test User {i}",
            }
            tasks.append(self.make_request("POST", "/auth/register", user_data))

        results = await asyncio.gather(*tasks)

        response_times = [r[0] for r in results]
        status_codes = [r[1] for r in results]

        response_times = [r[0] for r in results]
        status_codes = [r[1] for r in results]
        error_responses = [r[2] for r in results if r[1] not in [200, 201]]

        return {
            "endpoint": "/auth/register",
            "total_requests": len(results),
            "successful_requests": status_codes.count(200) + status_codes.count(201),
            "failed_requests": len([s for s in status_codes if s not in [200, 201]]),
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[18]
            if len(response_times) > 1
            else max(response_times),
            "errors": error_responses[:5],  # Show first 5 error responses
        }

    async def test_auth_login(self, num_logins: int = 5) -> Dict:
        """Test user login with existing users"""
        print(f"🔐 Testing user login with {num_logins} concurrent logins...")

        # First register a test user
        user_data = {
            "email": "logintest@example.com",
            "password": "testpassword123",
            "full_name": "Login Test User",
        }
        await self.make_request("POST", "/auth/register", user_data)

        # Now test concurrent logins
        login_data = {"email": "logintest@example.com", "password": "testpassword123"}

        tasks = []
        for _ in range(num_logins):
            tasks.append(self.make_request("POST", "/auth/login", login_data))

        results = await asyncio.gather(*tasks)

        response_times = [r[0] for r in results]
        status_codes = [r[1] for r in results]

        response_times = [r[0] for r in results]
        status_codes = [r[1] for r in results]
        error_responses = [r[2] for r in results if r[1] not in [200, 201]]

        return {
            "endpoint": "/auth/login",
            "total_requests": len(results),
            "successful_requests": status_codes.count(200) + status_codes.count(201),
            "failed_requests": len([s for s in status_codes if s not in [200, 201]]),
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[18]
            if len(response_times) > 1
            else max(response_times),
            "errors": error_responses[:5],  # Show first 5 error responses
        }

    async def run_load_test(self) -> Dict:
        """Run comprehensive load test"""
        print("🚀 Starting Goblin Assistant Load Test")
        print("=" * 50)

        results = {}

        # Test 1: Health endpoint with concurrent users
        results["health_test"] = await self.test_health_endpoint(20)

        # Test 2: User registration
        results["registration_test"] = await self.test_auth_registration(10)

        # Test 3: User login
        results["login_test"] = await self.test_auth_login(15)

        return results


def print_results(results: Dict):
    """Print formatted test results"""
    print("\n📊 LOAD TEST RESULTS")
    print("=" * 50)

    for test_name, data in results.items():
        print(f"\n🔍 {test_name.upper().replace('_', ' ')}")
        print("-" * 30)
        print(f"Endpoint: {data['endpoint']}")
        print(f"Total Requests: {data['total_requests']}")
        print(f"Successful: {data['successful_requests']}")
        print(f"Failed: {data['failed_requests']}")
        print(".3f")
        print(".3f")
        print(".3f")
        print(".3f")

        if data.get("errors"):
            print(f"Sample Errors: {data['errors'][:3]}")  # Show first 3 errors

    # Overall assessment
    total_requests = sum(data["total_requests"] for data in results.values())
    total_successful = sum(data["successful_requests"] for data in results.values())
    total_failed = sum(data["failed_requests"] for data in results.values())
    avg_response_time = statistics.mean(
        [data["avg_response_time"] for data in results.values()]
    )

    print("\n🎯 OVERALL PERFORMANCE")
    print("-" * 30)
    print(f"Total Requests: {total_requests}")
    print(f"Success Rate: {(total_successful / total_requests) * 100:.1f}%")
    print(".3f")

    if total_failed == 0 and avg_response_time < 1.0:
        print("✅ EXCELLENT: System handles concurrent load well!")
    elif total_failed < total_requests * 0.1 and avg_response_time < 2.0:
        print("⚠️  GOOD: Minor issues but acceptable performance")
    else:
        print("❌ POOR: Significant performance issues detected")


async def main():
    """Main load testing function"""
    async with LoadTester() as tester:
        results = await tester.run_load_test()
        print_results(results)


if __name__ == "__main__":
    asyncio.run(main())
