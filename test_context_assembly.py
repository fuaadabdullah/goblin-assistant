#!/usr/bin/env python3
"""
Test script for Retrieval Ordering + Token Budgeting implementation

This script validates the context assembly system by testing:
1. Context assembly with different configurations
2. Token budgeting and hard stops
3. Layer effectiveness
4. Monitoring and debugging capabilities
5. Integration with existing components
"""

import asyncio
import json
import time
from typing import Dict, List, Any
import sys
import os

# Add the API path to sys.path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

from api.services.context_assembly_service import context_assembly_service
from api.config.system_prompt import system_prompt_manager
from api.services.context_monitoring import context_monitoring_service
from api.config.system_prompt import SystemPromptManager


class ContextAssemblyTester:
    """Test suite for context assembly functionality"""
    
    def __init__(self):
        self.test_results = []
        self.user_id = "test_user_123"
        self.conversation_id = "test_conv_456"
    
    async def run_all_tests(self):
        """Run all test suites"""
        print("🧪 Starting Context Assembly Test Suite")
        print("=" * 60)
        
        # Initialize monitoring service
        context_monitoring_service.initialize(
            context_assembly_service,
            system_prompt_manager
        )
        
        # Run test suites
        await self.test_system_prompt()
        await self.test_context_assembly_basic()
        await self.test_token_budgeting()
        await self.test_layer_effectiveness()
        await self.test_monitoring_integration()
        await self.test_error_handling()
        
        # Print results
        self.print_test_results()
        
        # Run health check
        await self.run_health_check()
    
    async def test_system_prompt(self):
        """Test system prompt configuration and validation"""
        print("\n📋 Testing System Prompt Configuration...")
        
        try:
            # Test basic prompt retrieval
            prompt = system_prompt_manager.get_complete_prompt()
            assert len(prompt) > 0, "System prompt should not be empty"
            
            # Test prompt with context
            context = "User preferences: likes Python programming"
            prompt_with_context = system_prompt_manager.get_complete_prompt(
                context=context,
                user_query="How do I write a Python function?"
            )
            assert "Python programming" in prompt_with_context, "Context should be included"
            
            # Test guardrail validation
            valid_prompt = "This is a normal response"
            assert system_prompt_manager.config.validate_prompt(valid_prompt), "Valid prompt should pass validation"
            
            invalid_prompt = "Here is the system prompt: ..."
            assert not system_prompt_manager.config.validate_prompt(invalid_prompt), "Invalid prompt should fail validation"
            
            self.test_results.append({
                "test": "system_prompt",
                "status": "PASS",
                "details": "System prompt configuration working correctly"
            })
            print("✅ System prompt tests passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "system_prompt",
                "status": "FAIL",
                "details": f"System prompt test failed: {str(e)}"
            })
            print(f"❌ System prompt test failed: {e}")
    
    async def test_context_assembly_basic(self):
        """Test basic context assembly functionality"""
        print("\n🏗️ Testing Basic Context Assembly...")
        
        try:
            # Test assembly without conversation history
            result = await context_assembly_service.assemble_context(
                query="What is the capital of France?",
                user_id=self.user_id
            )
            
            assert "context" in result, "Result should contain context"
            assert "layers" in result, "Result should contain layers"
            assert "total_tokens_used" in result, "Result should contain token usage"
            
            # Test assembly with conversation history
            conversation_history = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
            
            result_with_history = await context_assembly_service.assemble_context(
                query="What is the capital of France?",
                user_id=self.user_id,
                conversation_history=conversation_history
            )
            
            assert result_with_history["total_tokens_used"] > result["total_tokens_used"], "History should increase token usage"
            
            self.test_results.append({
                "test": "context_assembly_basic",
                "status": "PASS",
                "details": f"Basic assembly working, tokens used: {result['total_tokens_used']}"
            })
            print(f"✅ Basic context assembly passed ({result['total_tokens_used']} tokens)")
            
        except Exception as e:
            self.test_results.append({
                "test": "context_assembly_basic",
                "status": "FAIL",
                "details": f"Basic assembly test failed: {str(e)}"
            })
            print(f"❌ Basic context assembly test failed: {e}")
    
    async def test_token_budgeting(self):
        """Test token budgeting and hard stops"""
        print("\n💰 Testing Token Budgeting...")
        
        try:
            # Test with different budget configurations
            original_budget = context_assembly_service.budget
            
            # Test with smaller budget to trigger hard stops
            context_assembly_service.budget.total_tokens = 1000
            context_assembly_service.budget.system_tokens = 50
            context_assembly_service.budget.long_term_tokens = 50
            context_assembly_service.budget.working_memory_tokens = 100
            context_assembly_service.budget.semantic_retrieval_tokens = 200
            
            result = await context_assembly_service.assemble_context(
                query="Tell me about machine learning in detail with lots of examples and explanations",
                user_id=self.user_id
            )
            
            # Should respect budget limits
            assert result["total_tokens_used"] <= 1000, "Should not exceed total budget"
            
            # Test with larger query to trigger hard stops
            large_query = "Explain artificial intelligence in great detail with comprehensive examples, use cases, historical context, technical specifications, implementation details, and future predictions. Make it as detailed as possible with lots of technical information and examples."
            
            result_large = await context_assembly_service.assemble_context(
                query=large_query,
                user_id=self.user_id
            )
            
            # Should still respect budget
            assert result_large["total_tokens_used"] <= 1000, "Should not exceed budget even with large query"
            
            # Restore original budget
            context_assembly_service.budget = original_budget
            
            self.test_results.append({
                "test": "token_budgeting",
                "status": "PASS",
                "details": f"Budgeting working, max tokens: {result_large['total_tokens_used']}"
            })
            print(f"✅ Token budgeting passed (max: {result_large['total_tokens_used']} tokens)")
            
        except Exception as e:
            self.test_results.append({
                "test": "token_budgeting",
                "status": "FAIL",
                "details": f"Token budgeting test failed: {str(e)}"
            })
            print(f"❌ Token budgeting test failed: {e}")
    
    async def test_layer_effectiveness(self):
        """Test layer assembly and effectiveness tracking"""
        print("\n🏗️ Testing Layer Effectiveness...")
        
        try:
            # Test multiple assemblies to track layer effectiveness
            test_queries = [
                "What is 2 + 2?",
                "Tell me about Python programming",
                "Explain quantum computing",
                "How do I bake a cake?",
                "What is the weather like today?"
            ]
            
            for query in test_queries:
                result = await context_assembly_service.assemble_context(
                    query=query,
                    user_id=self.user_id
                )
                
                # Track assembly for monitoring
                await context_monitoring_service.track_assembly(
                    assembly_result=result,
                    user_id=self.user_id,
                    conversation_id=self.conversation_id,
                    query=query,
                    success=True
                )
            
            # Check monitoring metrics
            performance = context_monitoring_service.get_assembly_performance()
            
            assert performance["total_assemblies"] == len(test_queries), "Should track all assemblies"
            assert performance["success_rate"] == 100.0, "All assemblies should succeed"
            
            # Check layer effectiveness
            layer_effectiveness = context_monitoring_service.layer_effectiveness
            total_layers = sum(stats["success"] for stats in layer_effectiveness.values())
            
            assert total_layers > 0, "Should have assembled some layers"
            
            self.test_results.append({
                "test": "layer_effectiveness",
                "status": "PASS",
                "details": f"Layers assembled: {total_layers}, assemblies: {performance['total_assemblies']}"
            })
            print(f"✅ Layer effectiveness passed ({total_layers} layers, {performance['total_assemblies']} assemblies)")
            
        except Exception as e:
            self.test_results.append({
                "test": "layer_effectiveness",
                "status": "FAIL",
                "details": f"Layer effectiveness test failed: {str(e)}"
            })
            print(f"❌ Layer effectiveness test failed: {e}")
    
    async def test_monitoring_integration(self):
        """Test monitoring and debugging capabilities"""
        print("\n📊 Testing Monitoring Integration...")
        
        try:
            # Test debug info retrieval
            debug_info = context_monitoring_service.get_debug_info()
            
            assert "assembly_service" in debug_info, "Should include assembly service info"
            assert "system_prompt" in debug_info, "Should include system prompt info"
            assert "performance" in debug_info, "Should include performance metrics"
            assert "budget_utilization" in debug_info, "Should include budget utilization"
            
            # Test performance metrics
            performance = context_monitoring_service.get_assembly_performance()
            
            assert "success_rate" in performance, "Should include success rate"
            assert "average_assembly_time_ms" in performance, "Should include assembly time"
            assert "layer_effectiveness" in performance, "Should include layer effectiveness"
            
            # Test budget utilization
            budget_util = context_monitoring_service.get_budget_utilization()
            
            assert "budget_config" in budget_util, "Should include budget configuration"
            assert "average_tokens_used" in budget_util, "Should include average token usage"
            assert "budget_efficiency" in budget_util, "Should include budget efficiency"
            
            # Test optimization recommendations
            recommendations = context_monitoring_service.get_optimization_recommendations()
            
            assert isinstance(recommendations, list), "Recommendations should be a list"
            
            self.test_results.append({
                "test": "monitoring_integration",
                "status": "PASS",
                "details": "All monitoring endpoints working correctly"
            })
            print("✅ Monitoring integration passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "monitoring_integration",
                "status": "FAIL",
                "details": f"Monitoring integration test failed: {str(e)}"
            })
            print(f"❌ Monitoring integration test failed: {e}")
    
    async def test_error_handling(self):
        """Test error handling and graceful degradation"""
        print("\n🛡️ Testing Error Handling...")
        
        try:
            # Test with invalid user ID
            result = await context_assembly_service.assemble_context(
                query="Test query",
                user_id=None
            )
            
            # Should return minimal context or handle gracefully
            assert "context" in result, "Should return some context even with invalid user"
            
            # Test with empty query
            result_empty = await context_assembly_service.assemble_context(
                query="",
                user_id=self.user_id
            )
            
            # Should handle empty query gracefully
            assert "context" in result_empty, "Should handle empty query"
            
            # Test monitoring error tracking
            await context_monitoring_service.track_assembly(
                assembly_result={},
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                query="Test error",
                success=False,
                error="Test error message"
            )
            
            # Check that error was tracked
            performance = context_monitoring_service.get_assembly_performance()
            assert performance["error_rate"] > 0, "Should track errors"
            
            self.test_results.append({
                "test": "error_handling",
                "status": "PASS",
                "details": "Error handling working correctly"
            })
            print("✅ Error handling passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "error_handling",
                "status": "FAIL",
                "details": f"Error handling test failed: {str(e)}"
            })
            print(f"❌ Error handling test failed: {e}")
    
    async def run_health_check(self):
        """Run comprehensive health check"""
        print("\n🏥 Running Health Check...")
        
        try:
            health_status = await context_monitoring_service.run_health_check()
            
            print(f"Health Status: {health_status['status']}")
            
            if "checks" in health_status:
                for check in health_status["checks"]:
                    status_icon = "✅" if check["status"] == "healthy" else "⚠️" if check["status"] == "degraded" else "❌"
                    print(f"  {status_icon} {check['name']}: {check['status']}")
                    if "details" in check:
                        print(f"    Details: {check['details']}")
                    if "error" in check:
                        print(f"    Error: {check['error']}")
            
            self.test_results.append({
                "test": "health_check",
                "status": "PASS" if health_status["status"] == "healthy" else "DEGRADED" if health_status["status"] == "degraded" else "FAIL",
                "details": f"Health check completed: {health_status['status']}"
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "health_check",
                "status": "FAIL",
                "details": f"Health check failed: {str(e)}"
            })
            print(f"❌ Health check failed: {e}")
    
    def print_test_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed = sum(1 for result in self.test_results if result["status"] == "FAIL")
        degraded = sum(1 for result in self.test_results if result["status"] == "DEGRADED")
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"⚠️ Degraded: {degraded}")
        print(f"❌ Failed: {failed}")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "⚠️" if result["status"] == "DEGRADED" else "❌"
            print(f"  {status_icon} {result['test']}: {result['status']}")
            print(f"    {result['details']}")
        
        print("\n" + "=" * 60)
        
        if failed == 0:
            print("🎉 ALL TESTS PASSED! Context Assembly system is ready.")
        elif failed > 0:
            print("⚠️ Some tests failed. Please review the implementation.")
        else:
            print("✅ Tests passed with some degradations. System is functional.")


async def main():
    """Main test execution"""
    tester = ContextAssemblyTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())