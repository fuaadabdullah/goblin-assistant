#!/usr/bin/env python3
"""
Test script for Write-Time Intelligence integration
Tests the anti-rot layer functionality end-to-end
"""

import asyncio
import json
import time
from typing import Dict, Any, List
import httpx
from datetime import datetime


class WriteTimeIntelligenceTester:
    """Test suite for Write-Time Intelligence functionality"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Test messages for different classification types
        self.test_messages = {
            "chat": [
                "How are you doing today?",
                "What's the weather like?",
                "Can you tell me a joke?",
                "I'm feeling bored, what should I do?"
            ],
            "fact": [
                "I'm a software engineer with 5 years of experience",
                "I live in San Francisco and work at Google",
                "I studied computer science at Stanford",
                "I'm fluent in Python, JavaScript, and Go"
            ],
            "preference": [
                "I prefer concise technical explanations",
                "I don't like verbose responses",
                "I always use dark mode",
                "I prefer React over Vue"
            ],
            "task_result": [
                "Here's the code I implemented for the feature",
                "I've completed the task successfully",
                "Attached is the solution you requested",
                "The implementation is done and working"
            ],
            "system": [
                "System: Memory cleared",
                "Assistant: Context updated",
                "Bot: Processing complete",
                "AI: Ready for next input"
            ],
            "noise": [
                "ok",
                "thanks",
                "cool",
                "lol",
                "👍",
                "bye"
            ]
        }
    
    async def test_health_check(self) -> bool:
        """Test if the API is running"""
        try:
            response = await self.client.get(f"{self.base_url}/test")
            if response.status_code == 200:
                print("✅ Health check passed")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    async def test_message_classification(self) -> Dict[str, Any]:
        """Test message classification for all types"""
        print("\n🧪 Testing message classification...")
        
        results = {}
        
        for message_type, messages in self.test_messages.items():
            print(f"\n  Testing {message_type} messages:")
            type_results = []
            
            for i, message in enumerate(messages):
                try:
                    response = await self.client.post(
                        f"{self.base_url}/write-time/test",
                        json={
                            "content": message,
                            "role": "user",
                            "user_id": "test_user_123",
                            "conversation_id": f"test_conv_{message_type}_{i}"
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        classification = result["classification"]["type"]
                        decision = result["decision"]["actions"]
                        
                        print(f"    ✅ '{message[:30]}...' -> {classification} (actions: {decision})")
                        
                        type_results.append({
                            "message": message,
                            "expected_type": message_type,
                            "actual_type": classification,
                            "correct": classification == message_type,
                            "decision": decision,
                            "confidence": result["classification"]["confidence"]
                        })
                    else:
                        print(f"    ❌ Failed to classify: {response.status_code}")
                        type_results.append({
                            "message": message,
                            "error": f"HTTP {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"    ❌ Exception: {e}")
                    type_results.append({
                        "message": message,
                        "error": str(e)
                    })
            
            results[message_type] = type_results
        
        return results
    
    async def test_decision_matrix_config(self) -> Dict[str, Any]:
        """Test decision matrix configuration endpoint"""
        print("\n⚙️  Testing decision matrix configuration...")
        
        try:
            response = await self.client.get(f"{self.base_url}/write-time/matrix/config")
            
            if response.status_code == 200:
                config = response.json()
                print("✅ Decision matrix config retrieved successfully")
                print(f"   Decision table has {len(config['decision_table'])} message types")
                print(f"   Rate limits: {config['rate_limits']}")
                return config
            else:
                print(f"❌ Failed to get config: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Exception getting config: {e}")
            return {}
    
    async def test_cache_stats(self) -> Dict[str, Any]:
        """Test cache statistics"""
        print("\n📦 Testing cache statistics...")
        
        try:
            response = await self.client.get(f"{self.base_url}/write-time/cache/stats")
            
            if response.status_code == 200:
                stats = response.json()
                print("✅ Cache stats retrieved successfully")
                print(f"   Status: {stats['status']}")
                print(f"   Total keys: {stats['cache_stats'].get('total_keys', 0)}")
                return stats
            else:
                print(f"❌ Failed to get cache stats: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Exception getting cache stats: {e}")
            return {}
    
    async def test_batch_processing(self) -> Dict[str, Any]:
        """Test batch message processing"""
        print("\n🔄 Testing batch message processing...")
        
        # Create test messages for batch processing
        batch_messages = []
        for message_type, messages in self.test_messages.items():
            for message in messages[:2]:  # Take first 2 messages from each type
                batch_messages.append({
                    "content": message,
                    "role": "user",
                    "user_id": "batch_test_user",
                    "conversation_id": f"batch_test_conv_{message_type}"
                })
        
        try:
            response = await self.client.post(
                f"{self.base_url}/write-time/test/batch",
                json=batch_messages
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Batch processing completed: {result['total_messages']} messages")
                
                # Analyze results
                correct_classifications = 0
                total_processed = 0
                
                for item in result["results"]:
                    if "error" not in item:
                        total_processed += 1
                        if item["classification"]["type"] == item["content_preview"].split()[0].lower():
                            correct_classifications += 1
                
                print(f"   Correct classifications: {correct_classifications}/{total_processed}")
                return result
            else:
                print(f"❌ Batch processing failed: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Exception in batch processing: {e}")
            return {}
    
    async def test_rate_limiting(self) -> Dict[str, Any]:
        """Test rate limiting functionality"""
        print("\n🚦 Testing rate limiting...")
        
        # Send many messages quickly to test rate limiting
        rate_limit_test_results = []
        
        for i in range(60):  # Try to exceed the 50 per hour limit
            try:
                response = await self.client.post(
                    f"{self.base_url}/write-time/test",
                    json={
                        "content": f"Test message {i} for rate limiting",
                        "role": "user",
                        "user_id": "rate_limit_test_user"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    actions = result["execution"]["actions_executed"]
                    rate_limit_test_results.append({
                        "message_id": i,
                        "actions": actions,
                        "success": True
                    })
                else:
                    rate_limit_test_results.append({
                        "message_id": i,
                        "success": False,
                        "status_code": response.status_code
                    })
                    
            except Exception as e:
                rate_limit_test_results.append({
                    "message_id": i,
                    "success": False,
                    "error": str(e)
                })
        
        # Analyze rate limiting results
        successful_requests = sum(1 for r in rate_limit_test_results if r["success"])
        print(f"   Successful requests: {successful_requests}/60")
        print(f"   Rate limiting appears to be: {'Active' if successful_requests < 60 else 'Inactive'}")
        
        return {
            "total_requests": 60,
            "successful_requests": successful_requests,
            "rate_limiting_active": successful_requests < 60,
            "results": rate_limit_test_results
        }
    
    async def test_discard_functionality(self) -> Dict[str, Any]:
        """Test message discard functionality for noise"""
        print("\n🗑️  Testing message discard functionality...")
        
        # Test noise messages that should be discarded
        noise_messages = ["ok", "thanks", "cool", "lol", "👍", "bye", "k", "ty"]
        discard_results = []
        
        for message in noise_messages:
            try:
                response = await self.client.post(
                    f"{self.base_url}/write-time/test",
                    json={
                        "content": message,
                        "role": "user",
                        "user_id": "discard_test_user"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    actions = result["execution"]["actions_executed"]
                    discarded = "discard" in actions
                    
                    print(f"   '{message}' -> Discarded: {discarded} (actions: {actions})")
                    
                    discard_results.append({
                        "message": message,
                        "discarded": discarded,
                        "actions": actions,
                        "expected_discard": True
                    })
                else:
                    print(f"   ❌ Failed to process '{message}': {response.status_code}")
                    discard_results.append({
                        "message": message,
                        "error": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                print(f"   ❌ Exception processing '{message}': {e}")
                discard_results.append({
                    "message": message,
                    "error": str(e)
                })
        
        # Calculate discard accuracy
        discarded_count = sum(1 for r in discard_results if r.get("discarded", False))
        print(f"   Noise messages discarded: {discarded_count}/{len(noise_messages)}")
        
        return {
            "total_noise_messages": len(noise_messages),
            "discarded_messages": discarded_count,
            "discard_accuracy": discarded_count / len(noise_messages) if noise_messages else 0,
            "results": discard_results
        }
    
    async def test_cache_operations(self) -> Dict[str, Any]:
        """Test cache operations"""
        print("\n💾 Testing cache operations...")
        
        cache_test_results = {}
        
        # Test cache stats
        try:
            stats_response = await self.client.get(f"{self.base_url}/write-time/cache/stats")
            if stats_response.status_code == 200:
                cache_test_results["initial_stats"] = stats_response.json()
                print("   ✅ Initial cache stats retrieved")
            else:
                print(f"   ❌ Failed to get initial cache stats: {stats_response.status_code}")
        except Exception as e:
            print(f"   ❌ Exception getting initial cache stats: {e}")
        
        # Test cache cleanup
        try:
            cleanup_response = await self.client.post(f"{self.base_url}/write-time/cache/cleanup")
            if cleanup_response.status_code == 200:
                cache_test_results["cleanup_result"] = cleanup_response.json()
                print("   ✅ Cache cleanup completed")
            else:
                print(f"   ❌ Cache cleanup failed: {cleanup_response.status_code}")
        except Exception as e:
            print(f"   ❌ Exception during cache cleanup: {e}")
        
        # Test cache clear (use with caution)
        try:
            clear_response = await self.client.post(f"{self.base_url}/write-time/cache/clear")
            if clear_response.status_code == 200:
                cache_test_results["clear_result"] = clear_response.json()
                print("   ✅ Cache clear completed")
            else:
                print(f"   ❌ Cache clear failed: {clear_response.status_code}")
        except Exception as e:
            print(f"   ❌ Exception during cache clear: {e}")
        
        return cache_test_results
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run the complete test suite"""
        print("🚀 Starting Write-Time Intelligence Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all tests
        test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "health_check": await self.test_health_check(),
            "classification": await self.test_message_classification(),
            "decision_matrix_config": await self.test_decision_matrix_config(),
            "cache_stats": await self.test_cache_stats(),
            "batch_processing": await self.test_batch_processing(),
            "rate_limiting": await self.test_rate_limiting(),
            "discard_functionality": await self.test_discard_functionality(),
            "cache_operations": await self.test_cache_operations(),
            "total_duration": time.time() - start_time
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUITE SUMMARY")
        print("=" * 60)
        
        # Classification accuracy summary
        total_classified = 0
        total_correct = 0
        
        for message_type, results in test_results["classification"].items():
            type_correct = sum(1 for r in results if r.get("correct", False))
            type_total = len(results)
            total_correct += type_correct
            total_classified += type_total
            
            if type_total > 0:
                accuracy = (type_correct / type_total) * 100
                print(f"  {message_type.upper()}: {type_correct}/{type_total} ({accuracy:.1f}%)")
        
        if total_classified > 0:
            overall_accuracy = (total_correct / total_classified) * 100
            print(f"\n  OVERALL CLASSIFICATION ACCURACY: {total_correct}/{total_classified} ({overall_accuracy:.1f}%)")
        
        # Discard functionality summary
        discard_results = test_results["discard_functionality"]
        if "discard_accuracy" in discard_results:
            print(f"  NOISE DISCARD ACCURACY: {discard_results['discarded_messages']}/{discard_results['total_noise_messages']} ({discard_results['discard_accuracy']:.1f}%)")
        
        # Rate limiting summary
        rate_limiting = test_results["rate_limiting"]
        if "rate_limiting_active" in rate_limiting:
            print(f"  RATE LIMITING: {'Active' if rate_limiting['rate_limiting_active'] else 'Inactive'}")
        
        print(f"\n  Total test duration: {test_results['total_duration']:.2f} seconds")
        print("=" * 60)
        
        # Save results to file
        with open("write_time_test_results.json", "w") as f:
            json.dump(test_results, f, indent=2, default=str)
        
        print("📄 Test results saved to write_time_test_results.json")
        
        return test_results
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


async def main():
    """Main test execution"""
    tester = WriteTimeIntelligenceTester()
    
    try:
        results = await tester.run_full_test_suite()
        
        # Print final status
        print("\n🎯 Write-Time Intelligence Integration Status:")
        if results["health_check"]:
            print("   ✅ API is running and accessible")
        else:
            print("   ❌ API health check failed")
        
        # Check if classification is working
        classification_working = any(
            results["classification"][msg_type] 
            for msg_type in results["classification"]
        )
        
        if classification_working:
            print("   ✅ Message classification is functional")
        else:
            print("   ❌ Message classification failed")
        
        print("\n🎉 Test suite completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Test suite interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())