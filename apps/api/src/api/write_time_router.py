"""
Write-Time Intelligence monitoring and testing endpoints
Provides insights into the anti-rot layer decision matrix
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from .services.cache_service import cache_service

router = APIRouter(prefix="/write-time", tags=["write-time"])


def _get_write_time_decision_matrix():
    from .services.write_time_matrix import WriteTimeDecisionMatrix

    return WriteTimeDecisionMatrix


def _get_write_time_intelligence():
    from .services.write_time_matrix import write_time_intelligence

    return write_time_intelligence


class TestMessageRequest(BaseModel):
    """Request to test message classification and decision matrix"""
    content: str
    role: str = "user"
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TestMessageResponse(BaseModel):
    """Response from message testing"""
    message_id: str
    classification: Dict[str, Any]
    decision: Dict[str, Any]
    execution: Dict[str, Any]
    processed_at: str


class CacheStatsResponse(BaseModel):
    """Response with cache statistics"""
    status: str
    cache_stats: Dict[str, Any]
    redis_info: Dict[str, Any]
    timestamp: str


class DecisionMatrixResponse(BaseModel):
    """Response with decision matrix configuration"""
    decision_table: Dict[str, Any]
    rate_limits: Dict[str, Any]
    timestamp: str


@router.post("/test", response_model=TestMessageResponse)
async def test_message_processing(request: TestMessageRequest):
    """
    Test message processing through Write-Time Intelligence
    
    This endpoint allows you to test how a message would be processed
    by the Write-Time Decision Matrix without actually storing it.
    """
    try:
        # Process message through Write-Time Intelligence
        write_time_intelligence = _get_write_time_intelligence()
        result = await write_time_intelligence.process_message(
            message_id=f"test_{datetime.utcnow().timestamp()}",
            content=request.content,
            role=request.role,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            metadata=request.metadata
        )
        
        return TestMessageResponse(
            message_id=result["message_id"],
            classification=result["classification"],
            decision=result["decision"],
            execution=result["execution"],
            processed_at=result["processed_at"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test processing failed: {str(e)}")


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """Get cache statistics and health information"""
    try:
        stats = await cache_service.get_cache_stats()
        return CacheStatsResponse(
            status=stats["status"],
            cache_stats=stats.get("cache_stats", {}),
            redis_info=stats.get("redis_info", {}),
            timestamp=stats.get("timestamp", datetime.utcnow().isoformat())
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.post("/cache/cleanup")
async def cleanup_cache():
    """Clean up expired cache entries"""
    try:
        result = await cache_service.cleanup_expired_keys()
        return {
            "status": result["status"],
            "message": result.get("message", "Cache cleanup completed"),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache cleanup failed: {str(e)}")


@router.get("/matrix/config", response_model=DecisionMatrixResponse)
async def get_decision_matrix_config():
    """Get the current decision matrix configuration"""
    try:
        WriteTimeDecisionMatrix = _get_write_time_decision_matrix()
        matrix = WriteTimeDecisionMatrix()
        
        config = {
            "decision_table": matrix.DECISION_TABLE,
            "rate_limits": {
                "max_embeddings_per_hour": matrix.MAX_EMBEDDINGS_PER_HOUR,
                "max_summaries_per_day": matrix.MAX_SUMMARIES_PER_DAY,
                "max_cache_size_mb": matrix.MAX_CACHE_SIZE_MB,
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return DecisionMatrixResponse(**config)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get matrix config: {str(e)}")


@router.get("/metrics")
async def get_write_time_metrics():
    """Get Write-Time Intelligence metrics and statistics"""
    try:
        # Get cache stats
        cache_stats = await cache_service.get_cache_stats()

        # Get decision matrix stats
        WriteTimeDecisionMatrix = _get_write_time_decision_matrix()
        matrix = WriteTimeDecisionMatrix()
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "cache": {
                "status": cache_stats.get("status", "unknown"),
                "total_keys": cache_stats.get("cache_stats", {}).get("total_keys", 0),
                "message_keys": cache_stats.get("cache_stats", {}).get("message_keys", 0),
                "context_keys": cache_stats.get("cache_stats", {}).get("context_keys", 0),
                "preference_keys": cache_stats.get("cache_stats", {}).get("preference_keys", 0),
            },
            "rate_limits": {
                "max_embeddings_per_hour": matrix.MAX_EMBEDDINGS_PER_HOUR,
                "max_summaries_per_day": matrix.MAX_SUMMARIES_PER_DAY,
                "embedding_counts": dict(matrix._embedding_counts),
                "summary_counts": dict(matrix._summary_counts),
            },
            "decision_matrix": {
                "message_types": list(matrix.DECISION_TABLE.keys()),
                "total_rules": len(matrix.DECISION_TABLE),
            }
        }
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cache data (use with caution)"""
    try:
        success = await cache_service.flush()
        if success:
            return {
                "status": "success",
                "message": "Cache cleared successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clear cache")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")


# Test data for common message types
TEST_MESSAGES = {
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


@router.get("/test/examples")
async def get_test_examples():
    """Get example messages for testing different classification types"""
    return {
        "examples": TEST_MESSAGES,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/test/batch")
async def test_batch_messages(messages: List[TestMessageRequest]):
    """Test multiple messages at once"""
    try:
        write_time_intelligence = _get_write_time_intelligence()
        results = []
        
        for i, message in enumerate(messages):
            result = await write_time_intelligence.process_message(
                message_id=f"batch_{i}_{datetime.utcnow().timestamp()}",
                content=message.content,
                role=message.role,
                user_id=message.user_id,
                conversation_id=message.conversation_id,
                metadata=message.metadata
            )
            
            results.append({
                "index": i,
                "content_preview": message.content[:50] + "..." if len(message.content) > 50 else message.content,
                "classification": result["classification"],
                "decision": result["decision"],
                "actions_taken": result["execution"]["actions_executed"]
            })
        
        return {
            "total_messages": len(messages),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch testing failed: {str(e)}")
