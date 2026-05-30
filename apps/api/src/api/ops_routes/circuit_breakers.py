from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from ..ops.security import require_ops_reset_access
from .shared import CircuitBreaker, circuit_breakers

router = APIRouter()


@router.get("/circuit-breakers")
async def circuit_breakers_status() -> Dict[str, Any]:
    try:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "circuit_breakers": {name: cb.get_status() for name, cb in circuit_breakers.items()},
            "summary": {
                "total_breakers": len(circuit_breakers),
                "open_breakers": len(
                    [cb for cb in circuit_breakers.values() if cb.state == "OPEN"]
                ),
                "half_open_breakers": len(
                    [cb for cb in circuit_breakers.values() if cb.state == "HALF_OPEN"]
                ),
                "closed_breakers": len(
                    [cb for cb in circuit_breakers.values() if cb.state == "CLOSED"]
                ),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Circuit breaker status failed: {str(e)}")


@router.post("/circuit-breakers/{provider_name}/reset")
@require_ops_reset_access()
async def reset_circuit_breaker(request: Request, provider_name: str) -> Dict[str, Any]:
    try:
        if provider_name not in circuit_breakers:
            circuit_breakers[provider_name] = CircuitBreaker()

        cb = circuit_breakers[provider_name]
        old_state = cb.state

        cb.failure_count = 0
        cb.state = "CLOSED"
        cb.last_failure_time = 0

        return {
            "success": True,
            "data": {
                "provider": provider_name,
                "status": "reset",
                "previous_state": old_state,
                "new_state": cb.state,
                "circuit_breaker": cb.get_status(),
            },
            "message": f"Circuit breaker for {provider_name} reset successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset circuit breaker: {str(e)}")
