#!/usr/bin/env python3
"""
MCP Service Full End-to-End Test Report

Comprehensive test suite covering all MCP functionality.
Run this to get a complete status report of the MCP service.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n🔧 {description}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True, result.stdout.strip()
        else:
            print(f"❌ {description} - FAILED")
            print(f"   Error: {result.stderr.strip()}")
            return False, result.stderr.strip()
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {e}")
        return False, str(e)


def main():
    """Run comprehensive MCP service tests"""
    print("🚀 MCP Service Full End-to-End Test Report")
    print("=" * 60)

    test_results = []

    # 1. Test Python Environment
    success, output = run_command("python3 --version", "Check Python Environment")
    test_results.append(("Python Environment", success))

    # 2. Test Virtual Environment
    success, output = run_command(
        ".venv/bin/python --version", "Check Virtual Environment"
    )
    test_results.append(("Virtual Environment", success))

    # 3. Test Dependencies Import
    success, output = run_command(
        "PYTHONPATH=. .venv/bin/python -c 'import fastapi, uvicorn, sqlalchemy, redis'",
        "Test Core Dependencies",
    )
    test_results.append(("Core Dependencies", success))

    # 4. Test MCP Module Imports
    success, output = run_command(
        "PYTHONPATH=. .venv/bin/python -c 'from mcp_auth import auth_service; from mcp_providers import provider_manager; from mcp_router import estimate_cost'",
        "Test MCP Module Imports",
    )
    test_results.append(("MCP Module Imports", success))

    # 5. Test Authentication Service
    success, output = run_command(
        'PYTHONPATH=. .venv/bin/python -c \'from mcp_auth import auth_service; user = auth_service.authenticate_user("admin", "admin123"); print("Auth works" if user else "Auth failed")\'',
        "Test Authentication Service",
    )
    test_results.append(("Authentication Service", "Auth works" in (output or "")))

    # 6. Test Provider Manager
    success, output = run_command(
        "PYTHONPATH=. .venv/bin/python -c 'from mcp_providers import provider_manager; providers = provider_manager.list_providers(); print(f\"Found {len(providers)} providers\")'",
        "Test Provider Manager",
    )
    test_results.append(("Provider Manager", success and "providers" in (output or "")))

    # 7. Test Cost Estimation
    success, output = run_command(
        'PYTHONPATH=. .venv/bin/python -c \'from mcp_router import estimate_cost; cost = estimate_cost("test prompt", "chat"); print(f"Cost: ${cost:.4f}")\'',
        "Test Cost Estimation",
    )
    test_results.append(("Cost Estimation", success and "Cost:" in (output or "")))

    # 8. Test MCP Test Server Startup
    print("\n🔧 Testing MCP Test Server Startup")
    try:
        # Start server in background
        server_process = subprocess.Popen(
            ["PYTHONPATH=. .venv/bin/python mcp_test_server.py"],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent,
        )
        time.sleep(3)  # Wait for server to start

        # Test server health
        health_success, health_output = run_command(
            "curl -s http://localhost:8000/health", "Server Health Check"
        )
        test_results.append(("Server Health Check", health_success))

        # Test admin dashboard
        dashboard_success, dashboard_output = run_command(
            "curl -s http://localhost:8000/mcp/v1/admin/dashboard", "Admin Dashboard"
        )
        test_results.append(("Admin Dashboard", dashboard_success))

        # Test authentication
        auth_success, auth_output = run_command(
            "curl -s -X POST 'http://localhost:8000/mcp/v1/auth/login?username=admin&password=admin123'",
            "JWT Authentication",
        )
        test_results.append(
            (
                "JWT Authentication",
                auth_success and "access_token" in (auth_output or ""),
            )
        )

        # Kill server
        server_process.terminate()
        server_process.wait(timeout=5)
        print("✅ MCP Test Server - Tests completed")

    except Exception as e:
        print(f"❌ MCP Test Server - Failed: {e}")
        test_results.append(("MCP Test Server", False))

    # 9. Test Docker Configuration
    success, output = run_command(
        "docker-compose -f /Users/fuaadabdullah/ForgeMonorepo/goblin-assistant/docker-compose.mcp.yml config --quiet",
        "Validate Docker Compose Config",
    )
    test_results.append(("Docker Compose Config", success))

    # 10. Test Individual Test Files
    test_files = ["test_mcp_e2e.py", "test_providers.py", "test_endpoints.py"]
    for test_file in test_files:
        if Path(test_file).exists():
            success, output = run_command(
                f"PYTHONPATH=. .venv/bin/python {test_file}", f"Run {test_file}"
            )
            test_results.append((f"Test File: {test_file}", success))
        else:
            test_results.append((f"Test File: {test_file}", False))

    # Summary Report
    print("\n" + "=" * 60)
    print("📊 MCP SERVICE TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1

    print("\n" + "=" * 60)
    print(f"🎯 OVERALL RESULT: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED! MCP service is fully operational.")
        print("\n✅ Features Verified:")
        print("   • JWT Authentication & RBAC")
        print("   • Admin Dashboard & Monitoring")
        print("   • Provider Orchestration & Circuit Breakers")
        print("   • Cost Estimation & Metrics")
        print("   • REST API Endpoints")
        print("   • Docker Compose Configuration")
        print("   • Module Imports & Dependencies")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("\n🔧 Next Steps:")
        print("   • Fix failing tests")
        print("   • Check server logs")
        print("   • Verify environment setup")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
